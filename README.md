# GATE Paper Processor

A Flask-based tool to automate uploading GATE exam PDFs and answer keys, cropping individual questions, uploading them to Cloudinary, and updating the database.

✨ Features
• Uploads GATE Question Paper PDF and Answer Key PDF via a web interface.
• Automatically splits & crops each question.
• Uploads question images to Cloudinary.
• Updates the MySQL database with question metadata.
• Flask web interface with file upload support.

📂 Project Structure

gate-paper-processor/
│── app.py # Flask app entry point
│── tk3_parser.py # PDF parsing & processing logic
│── cloudinary_config.py # Cloudinary integration
│── requirements.txt # Dependencies
│── templates/ # Flask HTML templates
│── uploads/ # Uploaded PDFs (ignored in .gitignore)
│── table_cropped_folder/ # Cropped question images (ignored in .gitignore)
│── .env # Environment variables (ignored in .gitignore)
│── .gitignore
└── README.md

⚡ Installation

1. Clone the repo

git clone https://github.com/SahilSoni27/gate-paper-processor.git
cd gate-paper-processor

2. Create virtual environment

python -m venv venv
source venv/bin/activate # macOS/Linux
venv\Scripts\activate # Windows

3. Install dependencies

pip install -r requirements.txt

🔧 Configuration

Create a .env file in the project root:

# Cloudinary

CLOUD_NAME=your_cloud
API_KEY=your_api_key
API_SECRET=your_api_secret

# Database (MySQL)

DB_HOST=localhost
DB_USER=root
DB_PASSWORD=root
DB_NAME=FMP

▶️ Usage

Run Flask app

python app.py

By default, it runs on http://127.0.0.1:5000/.

Upload PDFs
• Open browser → go to http://127.0.0.1:5000/
• Upload Question Paper PDF + Answer Key PDF
• The system will: 1. Process & crop questions 2. Upload question images to Cloudinary 3. Update database with mappings
