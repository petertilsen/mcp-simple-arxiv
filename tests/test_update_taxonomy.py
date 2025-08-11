"""
Unit tests for update_taxonomy module.
"""

import json
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, mock_open

# Add a mock reconfigure method to stdin/stdout if it doesn't exist
if not hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure = lambda **kwargs: None
if not hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure = lambda **kwargs: None

from mcp_simple_arxiv.update_taxonomy import update_taxonomy_file, load_taxonomy, TAXONOMY_FILE
from mcp_simple_arxiv.categories import CATEGORIES


class TestUpdateTaxonomy:
    """Test cases for update_taxonomy module."""

    def test_taxonomy_file_path(self):
        """Test that TAXONOMY_FILE points to the correct location."""
        expected_path = Path(__file__).parent.parent / "mcp_simple_arxiv" / "taxonomy.json"
        assert TAXONOMY_FILE == expected_path

    @patch('builtins.open', new_callable=mock_open)
    @patch('builtins.print')
    def test_update_taxonomy_file(self, mock_print, mock_file):
        """Test updating taxonomy file."""
        result = update_taxonomy_file()
        
        # Should return the CATEGORIES dictionary
        assert result == CATEGORIES
        
        # Should write to the correct file
        mock_file.assert_called_once_with(TAXONOMY_FILE, 'w', encoding='utf-8')
        
        # Should write JSON data
        handle = mock_file.return_value.__enter__.return_value
        written_data = ''.join(call.args[0] for call in handle.write.call_args_list)
        parsed_data = json.loads(written_data)
        assert parsed_data == CATEGORIES
        
        # Should print status messages
        assert mock_print.call_count == 2
        mock_print.assert_any_call(f"Creating taxonomy file at {TAXONOMY_FILE}...")
        mock_print.assert_any_call("Done!")

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('builtins.print')
    def test_load_taxonomy_file_exists(self, mock_print, mock_file, mock_exists):
        """Test loading taxonomy when file exists."""
        mock_exists.return_value = True
        
        # Mock file content
        test_taxonomy = {"test": {"name": "Test", "subcategories": {}}}
        mock_file.return_value.read.return_value = json.dumps(test_taxonomy)
        
        result = load_taxonomy()
        
        assert result == test_taxonomy
        
        # Should read from the correct file
        mock_file.assert_called_once_with(TAXONOMY_FILE, 'r', encoding='utf-8')
        
        # Should print loading message
        mock_print.assert_called_once_with(f"Loading taxonomy from {TAXONOMY_FILE}")

    @patch('pathlib.Path.exists')
    @patch('mcp_simple_arxiv.update_taxonomy.update_taxonomy_file')
    @patch('builtins.print')
    def test_load_taxonomy_file_not_exists(self, mock_print, mock_update, mock_exists):
        """Test loading taxonomy when file doesn't exist."""
        mock_exists.return_value = False
        mock_update.return_value = CATEGORIES
        
        result = load_taxonomy()
        
        assert result == CATEGORIES
        
        # Should call update_taxonomy_file
        mock_update.assert_called_once()
        
        # Should print creation message
        mock_print.assert_called_once_with(f"Taxonomy file not found at {TAXONOMY_FILE}, creating it...")

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('builtins.print')
    def test_load_taxonomy_json_error(self, mock_print, mock_file, mock_exists):
        """Test loading taxonomy with JSON parsing error."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "invalid json"
        
        with pytest.raises(json.JSONDecodeError):
            load_taxonomy()

    @patch('pathlib.Path.exists')
    @patch('builtins.open')
    @patch('builtins.print')
    def test_load_taxonomy_file_error(self, mock_print, mock_open, mock_exists):
        """Test loading taxonomy with file reading error."""
        mock_exists.return_value = True
        mock_open.side_effect = IOError("File read error")
        
        with pytest.raises(IOError):
            load_taxonomy()

    def test_categories_structure(self):
        """Test that CATEGORIES has the expected structure."""
        assert isinstance(CATEGORIES, dict)
        
        # Check that all primary categories have required structure
        for primary_key, primary_data in CATEGORIES.items():
            assert isinstance(primary_key, str)
            assert isinstance(primary_data, dict)
            assert "name" in primary_data
            assert "subcategories" in primary_data
            assert isinstance(primary_data["name"], str)
            assert isinstance(primary_data["subcategories"], dict)
            
            # Check subcategories structure
            for sub_key, sub_name in primary_data["subcategories"].items():
                assert isinstance(sub_key, str)
                assert isinstance(sub_name, str)

    def test_categories_content(self):
        """Test that CATEGORIES contains expected categories."""
        # Test some known categories
        assert "cs" in CATEGORIES
        assert CATEGORIES["cs"]["name"] == "Computer Science"
        assert "AI" in CATEGORIES["cs"]["subcategories"]
        assert CATEGORIES["cs"]["subcategories"]["AI"] == "Artificial Intelligence"
        
        assert "math" in CATEGORIES
        assert CATEGORIES["math"]["name"] == "Mathematics"
        
        assert "physics" in CATEGORIES
        assert CATEGORIES["physics"]["name"] == "Physics"

    @patch('builtins.open', new_callable=mock_open)
    @patch('builtins.print')
    def test_update_taxonomy_file_write_error(self, mock_print, mock_file):
        """Test update_taxonomy_file with write error."""
        mock_file.side_effect = IOError("Write error")
        
        with pytest.raises(IOError):
            update_taxonomy_file()

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    @patch('builtins.print')
    def test_update_taxonomy_file_json_error(self, mock_print, mock_json_dump, mock_file):
        """Test update_taxonomy_file with JSON serialization error."""
        mock_json_dump.side_effect = TypeError("JSON serialization error")
        
        with pytest.raises(TypeError):
            update_taxonomy_file()

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('builtins.print')
    def test_load_taxonomy_empty_file(self, mock_print, mock_file, mock_exists):
        """Test loading taxonomy from empty file."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = ""
        
        with pytest.raises(json.JSONDecodeError):
            load_taxonomy()

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('builtins.print')
    def test_load_taxonomy_malformed_json(self, mock_print, mock_file, mock_exists):
        """Test loading taxonomy from file with malformed JSON."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = '{"incomplete": json'
        
        with pytest.raises(json.JSONDecodeError):
            load_taxonomy()

    def test_categories_completeness(self):
        """Test that CATEGORIES contains all major arXiv categories."""
        expected_categories = [
            "cs",      # Computer Science
            "econ",    # Economics
            "eess",    # Electrical Engineering and Systems Science
            "math",    # Mathematics
            "physics", # Physics
            "q-bio",   # Quantitative Biology
            "q-fin",   # Quantitative Finance
            "stat",    # Statistics
        ]
        
        for category in expected_categories:
            assert category in CATEGORIES, f"Missing category: {category}"

    def test_cs_subcategories_completeness(self):
        """Test that Computer Science subcategories are complete."""
        cs_subcategories = CATEGORIES["cs"]["subcategories"]
        
        # Test some important CS subcategories
        expected_subcategories = [
            "AI",  # Artificial Intelligence
            "LG",  # Machine Learning
            "CV",  # Computer Vision and Pattern Recognition
            "CL",  # Computation and Language
            "RO",  # Robotics
            "CR",  # Cryptography and Security
        ]
        
        for subcategory in expected_subcategories:
            assert subcategory in cs_subcategories, f"Missing CS subcategory: {subcategory}"
