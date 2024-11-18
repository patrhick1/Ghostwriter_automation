# airtable_utils.py

import os
from pyairtable import Table
from dotenv import dotenv_values
import logging

# Load environment variables from .env file
secrets = dotenv_values(".env")

# Airtable Personal Access Token and Base ID from environment variables
AIRTABLE_PERSONAL_TOKEN = secrets.get("AIRTABLE_PERSONAL_TOKEN")
BASE_ID = secrets.get("AIRTABLE_BASE_ID")

# Table names in Airtable (Replace with your actual table names)
GENERATION_REQUESTS_TABLE_NAME = 'Generation Form Request'
GENERATED_CONTENT_TABLE_NAME = 'Python Automation Generated Content'
USERS_TABLE_NAME = 'Accounts (Users)'
TEMPLATES_TABLE_NAME = 'Templates'
SOURCES_TABLE_NAME = 'Sources'
QA_PAIRS_TABLE_NAME = 'QA Pairs'

class AirtableClient:
    def __init__(self):
        try:
            self.api_token = AIRTABLE_PERSONAL_TOKEN
            self.base_id = BASE_ID

            if not self.api_token or not self.base_id:
                raise ValueError("Airtable API token or Base ID is missing.")

            # Initialize tables
            self.generation_requests_table = Table(self.api_token, self.base_id, GENERATION_REQUESTS_TABLE_NAME)
            self.generated_content_table = Table(self.api_token, self.base_id, GENERATED_CONTENT_TABLE_NAME)
            self.users_table = Table(self.api_token, self.base_id, USERS_TABLE_NAME)
            self.templates_table = Table(self.api_token, self.base_id, TEMPLATES_TABLE_NAME)
            self.sources_table = Table(self.api_token, self.base_id, SOURCES_TABLE_NAME)
            self.qa_pairs_table = Table(self.api_token, self.base_id, QA_PAIRS_TABLE_NAME)
        except Exception as e:
            logging.error(f"Error initializing AirtableClient: {e}")
            raise

    def get_new_generation_requests(self, last_processed_time):
        """
        Fetch generation requests created after the last processed time
        """
        try:
            formula = f"IS_AFTER(CREATED_TIME(), '{last_processed_time}')"
            requests = self.generation_requests_table.all(formula=formula)
            return requests
        except Exception as e:
            logging.error(f"Error fetching new generation requests: {e}")
            return []

    def get_latest_created_time(self):
        """
        Get the latest 'Created Time' from the Generation Requests table
        """
        try:
            records = self.generation_requests_table.all()
            if records:
                # Sort records by 'Created Time' in descending order
                records.sort(key=lambda x: x['createdTime'], reverse=True)
                latest_time = records[0]['createdTime']
                return latest_time
            else:
                return None
        except Exception as e:
            logging.error(f"Error getting latest created time: {e}")
            return None

    def get_user_by_id(self, user_id):
        
        """
        Fetch user record by ID
        """
        try:
            user = self.users_table.get(user_id)
            return user
        except Exception as e:
            logging.error(f"Error fetching user with ID {user_id}: {e}")
            return None

    def get_templates(self, content_format, tags=None, category=None):
        # Build formula for filtering templates
        try:
            conditions = []
            if content_format:
                conditions.append("{{Content Format}}='{}'".format(content_format))
            if category:
                conditions.append("{{AAAA Category}}='{}'".format(category))
            if tags:
                tag_conditions = ["{{Tag}}='{}'".format(tag) for tag in tags]
                tag_formula = "OR(" + ",".join(tag_conditions) + ")"
                conditions.append(tag_formula)
            if conditions:
                formula = "AND(" + ",".join(conditions) + ")"
                templates = self.templates_table.all(formula=formula)
            else:
                templates = self.templates_table.all()
            return templates
        except Exception as e:
            logging.error(f"Error fetching templates: {e}")
            return []

    def get_sources_by_ids(self, source_ids):
        # Fetch sources by a list of IDs
        sources = []
        try:
            for source_id in source_ids:
                source = self.sources_table.get(source_id)
                sources.append(source)
            return sources
        except Exception as e:
            logging.error(f"Error fetching sources: {e}")
            return sources

    def get_random_qa_pair(self, source_ids):
        # Fetch QA pairs, optionally filtering by source IDs
        try:
            if source_ids:
                # Build formula to filter by source IDs
                source_conditions = ["{{Source_ID}}='{}'".format(source_id) for source_id in source_ids]
                source_formula = "OR(" + ",".join(source_conditions) + ")"
                qa_pairs = self.qa_pairs_table.all(formula=source_formula)
            else:
                qa_pairs = self.qa_pairs_table.all()
            # Select a random QA pair
            if qa_pairs:
                import random
                qa_pair = random.choice(qa_pairs)
                return qa_pair
            else:
                return None
        except Exception as e:
            logging.error(f"Error fetching random QA pair: {e}")
            return None

    def save_generated_content(self, fields):
        # Save generated content to Airtable
        try:
            self.generated_content_table.create(fields)
        except Exception as e:
            logging.error(f"Error saving generated content: {e}")

    def get_sample_content(self, user):
        # Get sample content from user record
        try:
            sample_content = user['fields'].get('Sample Content', '')
            return sample_content
        except Exception as e:
            logging.error(f"Error getting sample content: {e}")
            return ''
