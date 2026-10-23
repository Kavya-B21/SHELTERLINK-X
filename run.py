import os
import sys
from app import create_app
from app.extensions import db
from app.utils.seed_data import seed_database
from app.models import User

app = create_app(os.environ.get('FLASK_ENV', 'development'))


def init_db_and_seed():
    """Ensure tables exist and seed default demonstration data."""
    with app.app_context():
        db.create_all()
        # Seed if empty
        if User.query.count() == 0:
            print("First run detected. Initializing database schema and demonstration data...")
            seed_database()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'seed':
        with app.app_context():
            db.create_all()
            seed_database()
            print("Database successfully seeded.")
        sys.exit(0)

    # Initialize tables and seed if first run
    init_db_and_seed()

    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'
    
    print(f"\n=======================================================")
    print(f"  SHELTERLINK X — Emergency Shelter Intelligence System")
    print(f"  Running locally on: http://127.0.0.1:{port}")
    print(f"  Default Demo Accounts:")
    print(f"    - Admin:       admin / Admin@12345")
    print(f"    - Coordinator: coordinator / Coord@12345")
    print(f"    - Manager:     manager / Manager@12345")
    print(f"    - Viewer:      viewer / Viewer@12345")
    print(f"=======================================================\n")

    app.run(host=host, port=port, debug=debug, use_reloader=False)
