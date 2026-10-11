import csv
import os
import tempfile
from data.generate_logs import generate_synthetic_logs


def test_synthetic_log_generation():
    """
    Verifies that the dataset generator creates valid CSV logs containing
    both benign background traffic and all 5 injected attack types.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "test_logs.csv")
        generate_synthetic_logs(output_file=csv_path, total_normal=100)

        assert os.path.exists(csv_path)

        attack_types_found = set()
        total_rows = 0

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

            # Verify schema
            expected_headers = [
                "id", "timestamp", "user", "ip", "event_type",
                "port", "bytes_transferred", "country", "session_id",
                "is_attack", "attack_type"
            ]
            for h in expected_headers:
                assert h in headers

            for row in reader:
                total_rows += 1
                if row["is_attack"] == "1":
                    attack_types_found.add(row["attack_type"])

        assert total_rows > 100

        # Verify all 5 attack scenarios from Section 8 are present in the synthetic dataset
        assert "brute_force" in attack_types_found
        assert "port_scan" in attack_types_found
        assert "data_exfiltration" in attack_types_found
        assert "account_compromise" in attack_types_found
        assert "privilege_escalation" in attack_types_found
