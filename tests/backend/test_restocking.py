"""
Tests for restocking API endpoints.
"""
import pytest


class TestRestockingRecommendations:
    """Test suite for restocking recommendation endpoint."""

    def test_get_recommendations_default_budget(self, client):
        """Test getting recommendations with default budget."""
        response = client.get("/api/restocking/recommendations")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_recommendations_with_budget(self, client):
        """Test that recommendations respect budget constraint."""
        response = client.get("/api/restocking/recommendations?budget=50000")
        assert response.status_code == 200

        data = response.json()
        total = sum(item["total_cost"] for item in data)
        assert total <= 50000

    def test_get_recommendations_zero_budget(self, client):
        """Test that zero budget returns no recommendations."""
        response = client.get("/api/restocking/recommendations?budget=0")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 0

    def test_recommendations_sorted_by_forecasted_demand(self, client):
        """Test that recommendations are sorted by forecasted demand descending."""
        response = client.get("/api/restocking/recommendations")
        data = response.json()

        for i in range(len(data) - 1):
            assert data[i]["forecasted_demand"] >= data[i + 1]["forecasted_demand"]

    def test_recommendation_required_fields(self, client):
        """Test that each recommendation has all required fields."""
        response = client.get("/api/restocking/recommendations")
        data = response.json()

        required_fields = [
            "id", "item_sku", "item_name", "forecasted_demand",
            "current_demand", "quantity_on_hand", "recommended_quantity",
            "unit_cost", "total_cost", "trend", "has_inventory_match"
        ]
        for item in data:
            for field in required_fields:
                assert field in item, f"Missing field: {field}"

    def test_recommendation_data_types(self, client):
        """Test that recommendation fields have correct types."""
        response = client.get("/api/restocking/recommendations")
        data = response.json()

        for item in data:
            assert isinstance(item["forecasted_demand"], int)
            assert isinstance(item["current_demand"], int)
            assert isinstance(item["quantity_on_hand"], int)
            assert isinstance(item["recommended_quantity"], int)
            assert isinstance(item["unit_cost"], (int, float))
            assert isinstance(item["total_cost"], (int, float))
            assert isinstance(item["has_inventory_match"], bool)

    def test_recommendation_positive_quantities(self, client):
        """Test that recommended quantities are positive."""
        response = client.get("/api/restocking/recommendations")
        data = response.json()

        for item in data:
            assert item["recommended_quantity"] > 0
            assert item["unit_cost"] > 0
            assert item["total_cost"] > 0

    def test_recommendation_total_cost_calculation(self, client):
        """Test that total_cost equals recommended_quantity * unit_cost."""
        response = client.get("/api/restocking/recommendations")
        data = response.json()

        for item in data:
            expected_cost = item["recommended_quantity"] * item["unit_cost"]
            assert abs(item["total_cost"] - expected_cost) < 0.01

    def test_recommendation_trend_values(self, client):
        """Test that trend field has valid values."""
        response = client.get("/api/restocking/recommendations")
        data = response.json()

        valid_trends = ["increasing", "stable", "decreasing"]
        for item in data:
            assert item["trend"] in valid_trends

    def test_recommendations_budget_limits_items(self, client):
        """Test that a smaller budget returns fewer or equal items than a larger budget."""
        small_response = client.get("/api/restocking/recommendations?budget=50000")
        large_response = client.get("/api/restocking/recommendations?budget=2000000")

        small_data = small_response.json()
        large_data = large_response.json()

        assert len(small_data) <= len(large_data)


class TestRestockingOrders:
    """Test suite for restocking order submission and retrieval."""

    def test_submit_restocking_order(self, client):
        """Test submitting a restocking order."""
        order_data = {
            "items": [
                {
                    "item_sku": "WDG-001",
                    "item_name": "Industrial Widget Type A",
                    "quantity": 450,
                    "unit_cost": 50.0
                }
            ],
            "total_budget": 22500.0
        }
        response = client.post("/api/restocking/orders", json=order_data)
        assert response.status_code == 200

        data = response.json()
        assert "order_number" in data
        assert data["order_number"].startswith("RST-")
        assert data["status"] == "Processing"

    def test_submitted_order_has_lead_time(self, client):
        """Test that submitted order has a valid lead time between 5-15 days."""
        order_data = {
            "items": [
                {
                    "item_sku": "FLT-405",
                    "item_name": "Oil Filter Cartridge",
                    "quantity": 950,
                    "unit_cost": 50.0
                }
            ],
            "total_budget": 47500.0
        }
        response = client.post("/api/restocking/orders", json=order_data)
        data = response.json()

        assert "lead_time_days" in data
        assert 5 <= data["lead_time_days"] <= 15

    def test_submitted_order_has_dates(self, client):
        """Test that submitted order has order_date and expected_delivery."""
        order_data = {
            "items": [
                {
                    "item_sku": "GSK-203",
                    "item_name": "High-Temperature Gasket",
                    "quantity": 600,
                    "unit_cost": 50.0
                }
            ],
            "total_budget": 30000.0
        }
        response = client.post("/api/restocking/orders", json=order_data)
        data = response.json()

        assert "order_date" in data
        assert "expected_delivery" in data
        assert "T" in data["order_date"]
        assert "T" in data["expected_delivery"]

    def test_submitted_order_required_fields(self, client):
        """Test that submitted order response has all required fields."""
        order_data = {
            "items": [{"item_sku": "WDG-001", "item_name": "Widget", "quantity": 10, "unit_cost": 50.0}],
            "total_budget": 500.0
        }
        response = client.post("/api/restocking/orders", json=order_data)
        data = response.json()

        required_fields = [
            "id", "order_number", "items", "status",
            "order_date", "expected_delivery", "total_value", "lead_time_days"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_get_restocking_orders(self, client):
        """Test retrieving all submitted restocking orders."""
        response = client.get("/api/restocking/orders")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_submitted_order_appears_in_list(self, client):
        """Test that a submitted order appears in the restocking orders list."""
        order_data = {
            "items": [{"item_sku": "TEST-001", "item_name": "Test Item", "quantity": 1, "unit_cost": 10.0}],
            "total_budget": 10.0
        }
        post_response = client.post("/api/restocking/orders", json=order_data)
        submitted_order = post_response.json()

        get_response = client.get("/api/restocking/orders")
        all_orders = get_response.json()

        order_ids = [o["id"] for o in all_orders]
        assert submitted_order["id"] in order_ids
