from flask import Flask, request, jsonify
from models import db, Order
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dog_walking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def create_tables():
    with app.app_context():
        db.create_all()

def is_valid_time(start_time, end_time):
    # Прогулка может длиться не более получаса
    if end_time - start_time > timedelta(minutes=30):
        return False
    
    # Прогулка может начинаться либо в начале часа, либо в половину
    if start_time.minute not in [0, 30]:
        return False
    
    # Самая ранняя прогулка может начинаться не ранее 7-ми утра
    if start_time.hour < 7:
        return False
    
    # Самая поздняя прогулка может начинаться не позднее 11-ти вечера
    if start_time.hour > 23:
        return False
    
    return True

@app.route('/orders/<date>', methods=['GET'])
def get_orders(date):
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    start_of_day = datetime(date_obj.year, date_obj.month, date_obj.day, 7, 0)
    end_of_day = datetime(date_obj.year, date_obj.month, date_obj.day, 23, 30)

    orders = Order.query.filter(Order.start_time >= start_of_day, Order.start_time <= end_of_day).all()

    result = []
    for order in orders:
        result.append({
            'apartment_number': order.apartment_number,
            'pet_name': order.pet_name,
            'breed': order.breed,
            'start_time': order.start_time.isoformat(),
            'end_time': order.end_time.isoformat()
        })

    return jsonify(result)

@app.route('/orders', methods=['POST'])
def create_order():
    data = request.json
    apartment_number = data.get('apartment_number')
    pet_name = data.get('pet_name')
    breed = data.get('breed')
    start_time_str = data.get('start_time')
    
    try:
        start_time = datetime.fromisoformat(start_time_str)
        end_time = start_time + timedelta(minutes=30)
    except ValueError:
        return jsonify({'error': 'Invalid start_time format. Use ISO format.'}), 400

    if not is_valid_time(start_time, end_time):
        return jsonify({'error': 'Invalid time for the walk.'}), 400

    # Проверяем, нет ли пересечений с другими заказами
    existing_orders = Order.query.filter(
        Order.start_time < end_time,
        Order.end_time > start_time
    ).all()

    if len(existing_orders) >= 2:  # Пётр и Антон могут гулять одновременно только с одним животным
        return jsonify({'error': 'No available slots for the given time.'}), 400

    new_order = Order(
        apartment_number=apartment_number,
        pet_name=pet_name,
        breed=breed,
        start_time=start_time,
        end_time=end_time
    )
    db.session.add(new_order)
    db.session.commit()

    return jsonify({
        'id': new_order.id,
        'apartment_number': new_order.apartment_number,
        'pet_name': new_order.pet_name,
        'breed': new_order.breed,
        'start_time': new_order.start_time.isoformat(),
        'end_time': new_order.end_time.isoformat()
    }), 201

if __name__ == '__main__':
    create_tables()  # Создаём таблицы до запуска сервера
    app.run(debug=True)
