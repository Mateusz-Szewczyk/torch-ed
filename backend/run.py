import os
import sys
from server import create_app
from server.config import load_private_keys
import dotenv

if __name__ == '__main__':
    try:
        load_private_keys()
    except ValueError as e:
        print(f"Error loading private keys: {e}")
        exit(1)

    # Check for flags
    is_testing = '-t' in sys.argv

    app = create_app(testing=is_testing)


    port: int = int(os.getenv('PORT', 14440))

    dotenv.load_dotenv()
    debug = os.getenv('DEBUG', 'false') == 'true'
    app.run(debug=True, host='0.0.0.0', port=port)
