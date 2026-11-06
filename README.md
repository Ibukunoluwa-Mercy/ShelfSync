# ShelfSync

ShelfSync is a Flask foundation for a small-shop inventory management system.
This first step includes shared layouts, brand styling, and the SQLite schema.

## Windows setup

From this directory, run:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open the temporary layout test at
<http://127.0.0.1:5000/_layout-test>.

The first application start creates `inventory.db` and the default Food,
Drinks, and Toiletries categories. No default user is created.

Set a strong `SECRET_KEY` environment variable before using the application
outside local development.
