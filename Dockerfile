# Use the official lightweight Python image.
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the rest of the app
COPY . .

# Streamlit settings to run the app
ENV STREAMLIT_PORT=7860
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLECORS=false
ENV STREAMLIT_SERVER_PORT=$STREAMLIT_PORT

# Expose port
EXPOSE $STREAMLIT_PORT

# Run the app
CMD ["streamlit", "run", "app.py"]
