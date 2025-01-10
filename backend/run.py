import os
import sys
from server import create_app
from server.config import load_private_keys

if __name__ == '__main__':
    try:
        load_private_keys()
    except ValueError as e:
        print(f"Error loading private keys: {e}")
        exit(1)

    if '-t' in sys.argv:
        app = create_app(testing=True)
    else:
        app = create_app()
    port: int = int(os.getenv('PORT', 14440))
    app.run(debug=True, host='0.0.0.0', port=port)