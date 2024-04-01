Start by installing the latest version of Python (3.11 as of Sept 2023).

Inside of the blackhole2 directory, create a new virtual environment:
py -3 -m venv .venv

Enter the virtual environment with:
.\.venv\Scripts\activate

Install all required packages with:
pip install -r requirements.txt

To start the server:
uvicorn main:blackhole_app --reload

While the server is running, you can view the Swagger page at:
http://127.0.0.1:8000/docs
