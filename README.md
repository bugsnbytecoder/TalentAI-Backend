Step 0: 
python3 -m venv venv
source venv/bin/activate

Step 1:
pip install -r requirements.txt

Step 2:
python manage.py makemigrations

Step 3:
python manage.py migrate
python3 manage.py generateschema --file openapi-schema.yml

Step 4:
python manage.py runserver

