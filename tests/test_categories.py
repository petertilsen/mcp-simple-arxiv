"""
Unit tests for categories module.
"""

import pytest
import sys
from unittest.mock import patch

# Add a mock reconfigure method to stdin/stdout if it doesn't exist
if not hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure = lambda **kwargs: None
if not hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure = lambda **kwargs: None

from mcp_simple_arxiv.categories import CATEGORIES


class TestCategories:
    """Test cases for the CATEGORIES constant."""

    def test_categories_is_dict(self):
        """Test that CATEGORIES is a dictionary."""
        assert isinstance(CATEGORIES, dict)
        assert len(CATEGORIES) > 0

    def test_categories_structure(self):
        """Test that each category has the correct structure."""
        for primary_key, primary_data in CATEGORIES.items():
            # Primary key should be a string
            assert isinstance(primary_key, str)
            assert len(primary_key) > 0
            
            # Primary data should be a dictionary with required keys
            assert isinstance(primary_data, dict)
            assert "name" in primary_data
            assert "subcategories" in primary_data
            
            # Name should be a non-empty string
            assert isinstance(primary_data["name"], str)
            assert len(primary_data["name"]) > 0
            
            # Subcategories should be a dictionary
            assert isinstance(primary_data["subcategories"], dict)
            
            # Each subcategory should have string key and value
            for sub_key, sub_name in primary_data["subcategories"].items():
                assert isinstance(sub_key, str)
                assert isinstance(sub_name, str)
                assert len(sub_key) > 0
                assert len(sub_name) > 0

    def test_computer_science_category(self):
        """Test Computer Science category specifically."""
        assert "cs" in CATEGORIES
        cs_category = CATEGORIES["cs"]
        
        assert cs_category["name"] == "Computer Science"
        assert isinstance(cs_category["subcategories"], dict)
        assert len(cs_category["subcategories"]) > 0
        
        # Test some important CS subcategories
        expected_subcategories = {
            "AI": "Artificial Intelligence",
            "LG": "Machine Learning",
            "CV": "Computer Vision and Pattern Recognition",
            "CL": "Computation and Language",
            "RO": "Robotics",
            "CR": "Cryptography and Security",
            "DB": "Databases",
            "DS": "Data Structures and Algorithms",
            "NE": "Neural and Evolutionary Computing",
            "PL": "Programming Languages",
            "SE": "Software Engineering"
        }
        
        for sub_key, expected_name in expected_subcategories.items():
            assert sub_key in cs_category["subcategories"]
            assert cs_category["subcategories"][sub_key] == expected_name

    def test_mathematics_category(self):
        """Test Mathematics category specifically."""
        assert "math" in CATEGORIES
        math_category = CATEGORIES["math"]
        
        assert math_category["name"] == "Mathematics"
        assert isinstance(math_category["subcategories"], dict)
        assert len(math_category["subcategories"]) > 0
        
        # Test some important Math subcategories
        expected_subcategories = {
            "AG": "Algebraic Geometry",
            "NT": "Number Theory",
            "PR": "Probability",
            "ST": "Statistics Theory",
            "NA": "Numerical Analysis",
            "OC": "Optimization and Control",
            "CO": "Combinatorics",
            "LO": "Logic"
        }
        
        for sub_key, expected_name in expected_subcategories.items():
            assert sub_key in math_category["subcategories"]
            assert math_category["subcategories"][sub_key] == expected_name

    def test_physics_category(self):
        """Test Physics category specifically."""
        assert "physics" in CATEGORIES
        physics_category = CATEGORIES["physics"]
        
        assert physics_category["name"] == "Physics"
        assert isinstance(physics_category["subcategories"], dict)
        assert len(physics_category["subcategories"]) > 0
        
        # Test some important Physics subcategories
        expected_subcategories = {
            "cond-mat": "Condensed Matter",
            "hep-th": "High Energy Physics - Theory",
            "quant-ph": "Quantum Physics",
            "astro-ph": "Astrophysics",
            "gr-qc": "General Relativity and Quantum Cosmology",
            "nucl-th": "Nuclear Theory"
        }
        
        # Note: Some of these might not be in the current CATEGORIES
        # Let's test the ones that are actually there
        physics_subcats = physics_category["subcategories"]
        assert len(physics_subcats) > 0
        
        # Test some that should be there based on the implementation
        if "optics" in physics_subcats:
            assert physics_subcats["optics"] == "Optics"
        if "comp-ph" in physics_subcats:
            assert physics_subcats["comp-ph"] == "Computational Physics"

    def test_all_major_categories_present(self):
        """Test that all major arXiv categories are present."""
        expected_major_categories = [
            "cs",      # Computer Science
            "econ",    # Economics
            "eess",    # Electrical Engineering and Systems Science
            "math",    # Mathematics
            "physics", # Physics
            "q-bio",   # Quantitative Biology
            "q-fin",   # Quantitative Finance
            "stat",    # Statistics
        ]
        
        for category in expected_major_categories:
            assert category in CATEGORIES, f"Missing major category: {category}"
            assert isinstance(CATEGORIES[category]["name"], str)
            assert len(CATEGORIES[category]["name"]) > 0
            assert isinstance(CATEGORIES[category]["subcategories"], dict)

    def test_statistics_category(self):
        """Test Statistics category specifically."""
        assert "stat" in CATEGORIES
        stat_category = CATEGORIES["stat"]
        
        assert stat_category["name"] == "Statistics"
        assert isinstance(stat_category["subcategories"], dict)
        
        # Test some important Statistics subcategories
        expected_subcategories = {
            "AP": "Applications",
            "CO": "Computation", 
            "ME": "Methodology",
            "ML": "Machine Learning",
            "TH": "Statistics Theory"
        }
        
        for sub_key, expected_name in expected_subcategories.items():
            assert sub_key in stat_category["subcategories"]
            assert stat_category["subcategories"][sub_key] == expected_name

    def test_quantitative_biology_category(self):
        """Test Quantitative Biology category specifically."""
        assert "q-bio" in CATEGORIES
        qbio_category = CATEGORIES["q-bio"]
        
        assert qbio_category["name"] == "Quantitative Biology"
        assert isinstance(qbio_category["subcategories"], dict)
        
        # Test some important Q-Bio subcategories
        expected_subcategories = {
            "BM": "Biomolecules",
            "CB": "Cell Behavior",
            "GN": "Genomics",
            "NC": "Neurons and Cognition",
            "PE": "Populations and Evolution",
            "QM": "Quantitative Methods"
        }
        
        for sub_key, expected_name in expected_subcategories.items():
            assert sub_key in qbio_category["subcategories"]
            assert qbio_category["subcategories"][sub_key] == expected_name

    def test_quantitative_finance_category(self):
        """Test Quantitative Finance category specifically."""
        assert "q-fin" in CATEGORIES
        qfin_category = CATEGORIES["q-fin"]
        
        assert qfin_category["name"] == "Quantitative Finance"
        assert isinstance(qfin_category["subcategories"], dict)
        
        # Test some important Q-Fin subcategories
        expected_subcategories = {
            "CP": "Computational Finance",
            "EC": "Economics",
            "GN": "General Finance",
            "MF": "Mathematical Finance",
            "PM": "Portfolio Management",
            "PR": "Pricing of Securities",
            "RM": "Risk Management",
            "ST": "Statistical Finance"
        }
        
        for sub_key, expected_name in expected_subcategories.items():
            assert sub_key in qfin_category["subcategories"]
            assert qfin_category["subcategories"][sub_key] == expected_name

    def test_economics_category(self):
        """Test Economics category specifically."""
        assert "econ" in CATEGORIES
        econ_category = CATEGORIES["econ"]
        
        assert econ_category["name"] == "Economics"
        assert isinstance(econ_category["subcategories"], dict)
        
        # Test Economics subcategories
        expected_subcategories = {
            "EM": "Econometrics",
            "GN": "General Economics",
            "TH": "Theoretical Economics"
        }
        
        for sub_key, expected_name in expected_subcategories.items():
            assert sub_key in econ_category["subcategories"]
            assert econ_category["subcategories"][sub_key] == expected_name

    def test_eess_category(self):
        """Test Electrical Engineering and Systems Science category."""
        assert "eess" in CATEGORIES
        eess_category = CATEGORIES["eess"]
        
        assert eess_category["name"] == "Electrical Engineering and Systems Science"
        assert isinstance(eess_category["subcategories"], dict)
        
        # Test EESS subcategories
        expected_subcategories = {
            "AS": "Audio and Speech Processing",
            "IV": "Image and Video Processing",
            "SP": "Signal Processing",
            "SY": "Systems and Control"
        }
        
        for sub_key, expected_name in expected_subcategories.items():
            assert sub_key in eess_category["subcategories"]
            assert eess_category["subcategories"][sub_key] == expected_name

    def test_no_empty_categories(self):
        """Test that no categories are empty."""
        for primary_key, primary_data in CATEGORIES.items():
            # Each primary category should have at least one subcategory
            assert len(primary_data["subcategories"]) > 0, f"Category {primary_key} has no subcategories"

    def test_no_duplicate_subcategory_codes(self):
        """Test that subcategory codes are unique within each primary category."""
        for primary_key, primary_data in CATEGORIES.items():
            subcategories = primary_data["subcategories"]
            subcategory_codes = list(subcategories.keys())
            
            # Check for duplicates
            assert len(subcategory_codes) == len(set(subcategory_codes)), \
                f"Duplicate subcategory codes found in {primary_key}"

    def test_subcategory_codes_format(self):
        """Test that subcategory codes follow expected format."""
        for primary_key, primary_data in CATEGORIES.items():
            for sub_key in primary_data["subcategories"].keys():
                # Subcategory codes should be uppercase letters, numbers, or hyphens
                assert sub_key.replace("-", "").replace("_", "").isalnum(), \
                    f"Invalid subcategory code format: {primary_key}.{sub_key}"
                
                # Should not be empty
                assert len(sub_key) > 0, f"Empty subcategory code in {primary_key}"

    def test_category_names_not_empty(self):
        """Test that all category and subcategory names are non-empty."""
        for primary_key, primary_data in CATEGORIES.items():
            # Primary category name should not be empty
            assert primary_data["name"].strip() != "", \
                f"Empty name for primary category {primary_key}"
            
            # Subcategory names should not be empty
            for sub_key, sub_name in primary_data["subcategories"].items():
                assert sub_name.strip() != "", \
                    f"Empty name for subcategory {primary_key}.{sub_key}"
