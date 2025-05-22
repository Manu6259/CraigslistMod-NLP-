````markdown
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
````

## 2. Run the Scrapy Spider

This step will scrape the Craigslist forums and save the raw data.

```bash
cd path/to/your/scrapy/project
scrapy crawl your_spider_name -o raw_data.csv
```

> **Note:** Replace `your_spider_name` with the name of your Scrapy spider.

## 3. Run the Data Cleaning Pipeline

Clean and preprocess the scraped data:


## 4. Run the Model Pipeline
