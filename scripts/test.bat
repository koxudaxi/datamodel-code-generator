python -m venv venv

venv\Scripts\activate.bat

pip install -e .[all] isort==4.3.21 "black>=19.10b0,<20"

pytest --cov=datamodel_code_generator --cov-report term-missing tests

deactivate.bat

del /f /s /q venv 1>nul
rmdir /s /q venv
