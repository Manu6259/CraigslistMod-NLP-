# Craigslist Forum Moderation with NLP

Built an automated content moderation pipeline for Craigslist forums by combining custom web scraping and transformer-based NLP. A Python-based scraper using Scrapy and BeautifulSoup was developed to extract over 2,000 forum posts, preserving thread hierarchy and metadata. The text data was then processed and classified using Hugging Face transformer models such as DehateBERT, IMSyPP, and BERT, achieving 98% accuracy in detecting toxic or harmful content.

---

# Dataset Setup and Pipeline

## 1. Install Dependencies

Make sure you have Python ≥ 3.7 installed, then run:

```bash
pip install \
  nltk>=3.6.5 \
  requests>=2.25.1 \
  beautifulsoup4>=4.9.3 \
  pandas>=1.2.0 \
  numpy>=1.19.0 \
  scikit-learn>=0.24.0 \
  transformers>=4.0.0
```

## 2. Run the Scrapy Spider

This step will scrape the Craigslist forums and save the raw data.

```bash
cd path/to/your/scrapy/project
scrapy crawl your_spider_name -o raw_data.csv
```

> **Note:** Replace `your_spider_name` with the name of your Scrapy spider.

## 3. Run the Data Cleaning Pipeline

Clean and preprocess the scraped data:

```bash
python clean_data.py
```

This script performs:
- Text normalization and stopword removal
- Thread structure flattening
- Metadata extraction

## 4. Run the Model Pipeline

Apply NLP models to classify the cleaned posts:

```bash
python run_model.py
```

This step:
- Loads the pre-trained transformer model (e.g., DehateBERT)
- Encodes input text using Hugging Face Tokenizers
- Outputs predictions and evaluation metrics (accuracy, precision, recall)

---
