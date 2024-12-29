import os
import sys
from server import create_app


if __name__ == '__main__':
    if '-t' in sys.argv:
        app = create_app(testing=True)
    else:
        app = create_app()
    port: int = int(os.getenv('PORT', 14440))
    app.run(debug=True, host='0.0.0.0', port=port)