"""
Tests for data ingestion pipeline
"""
import unittest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from faker import Faker

# Assuming these are your actual module paths
from app.models.database import Base, Equipment, EquipmentType, SensorReading
from app.services.ingestion import DataIngestionPipeline

fake = Faker()

# Test database setup (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(bind=engine)


class TestDataIngestionPipeline(unittest.TestCase):
    """
    Test suite for DataIngestionPipeline using unittest
    """

    @classmethod
    def setUpClass(cls):
        """Create tables once for the whole test class"""
        Base.metadata.create_all(bind=engine)

    @classmethod
    def tearDownClass(cls):
        """Drop tables after all tests are done"""
        Base.metadata.drop_all(bind=engine)

    def setUp(self):
        """Run before every test - fresh session + test equipment"""
        self.session = TestSessionLocal()

        # Create test equipment (appears in every test)
        self.equipment = Equipment(
            equipment_id="TEST-001",
            equipment_type=EquipmentType.GAS_DETECTOR,
            manufacturer="Test Corp",
            model="Test Model",
            serial_number="TEST-SN-001"
        )
        self.session.add(self.equipment)
        self.session.commit()

        # Create pipeline instance for this test
        self.pipeline = DataIngestionPipeline(self.session)

    def tearDown(self):
        """Run after every test - clean session"""
        self.session.close()

    def test_ingest_valid_readings(self):
        """Test ingestion of valid sensor readings"""
        readings = [
            {
                "equipment_id": "TEST-001",
                "metric_name": "gas_concentration",
                "metric_value": 5.2,
                "metric_unit": "ppm",
                "time": datetime.utcnow(),
                "reading_status": "normal"
            },
            {
                "equipment_id": "TEST-001",
                "metric_name": "temperature",
                "metric_value": 22.5,
                "metric_unit": "celsius",
                "time": datetime.utcnow(),
                "reading_status": "normal"
            }
        ]

        result = self.pipeline.ingest_batch(readings)

        self.assertTrue(result["success"])
        self.assertEqual(result["total_inserted"], 2)
        self.assertEqual(result["invalid_count"], 0)
        self.assertEqual(result["duplicate_count"], 0)

    def test_reject_invalid_readings(self):
        """Test that invalid readings are rejected"""
        readings = [
            {
                "equipment_id": "TEST-001",
                "metric_name": "gas_concentration",
                "metric_value": "not_a_number",  # Invalid: string instead of float
                "time": datetime.utcnow()
            },
            {
                "equipment_id": "NONEXISTENT",  # Invalid: equipment doesn't exist
                "metric_name": "temperature",
                "metric_value": 25.0,
                "time": datetime.utcnow()
            }
        ]

        result = self.pipeline.ingest_batch(readings)

        self.assertTrue(result["success"])           # usually still "success" even with invalids
        self.assertEqual(result["total_inserted"], 0)
        self.assertEqual(result["invalid_count"], 2)

    def test_deduplicate_readings(self):
        """Test that duplicate readings are removed/handled"""
        timestamp = datetime.utcnow()
        readings = [
            {
                "equipment_id": "TEST-001",
                "metric_name": "gas_concentration",
                "metric_value": 5.0,
                "time": timestamp
            },
            {
                "equipment_id": "TEST-001",
                "metric_name": "gas_concentration",
                "metric_value": 5.0,
                "time": timestamp  # Duplicate
            }
        ]

        result = self.pipeline.ingest_batch(readings)

        self.assertTrue(result["success"])
        self.assertEqual(result["total_inserted"], 1)
        self.assertEqual(result["duplicate_count"], 1)

    def test_detect_late_arrivals(self):
        """Test detection of late-arriving data"""
        readings = [
            {
                "equipment_id": "TEST-001",
                "metric_name": "temperature",
                "metric_value": 25.0,
                "time": datetime.utcnow() - timedelta(hours=2)  # 2 hours old
            }
        ]

        result = self.pipeline.ingest_batch(readings)

        self.assertTrue(result["success"])
        self.assertEqual(result.get("late_arrival_count", 0), 1)

    def test_batch_performance(self):
        """Test that batch ingestion performs well with larger datasets"""
        readings = []
        for i in range(1000):
            readings.append({
                "equipment_id": "TEST-001",
                "metric_name": "gas_concentration",
                "metric_value": fake.pyfloat(min_value=0, max_value=10),
                "time": datetime.utcnow() - timedelta(seconds=i),
                "reading_status": "normal"
            })

        result = self.pipeline.ingest_batch(readings)

        self.assertTrue(result["success"])
        self.assertEqual(result["total_inserted"], 1000)
        # Adjust threshold depending on your machine / actual performance
        self.assertLess(result.get("processing_time_ms", 9999), 5000)

    def test_unreasonable_values_rejected(self):
        """Test that unreasonable sensor values are rejected"""
        readings = [
            {
                "equipment_id": "TEST-001",
                "metric_name": "temperature",
                "metric_value": 999999.0,  # Unreasonably high
                "time": datetime.utcnow()
            }
        ]

        result = self.pipeline.ingest_batch(readings)

        self.assertEqual(result["invalid_count"], 1)
        self.assertEqual(result["total_inserted"], 0)


if __name__ == "__main__":
    unittest.main()