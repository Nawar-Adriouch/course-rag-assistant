FROM python:3.11-slim

WORKDIR /code

COPY requirements.txt .
#pytorch une biblio utilisé pour l'execution des modeles de l'intellegence artificielle 
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8501

CMD ["streamlit", "run", "app/main.py", "--server.address=0.0.0.0", "--server.port=8501"]