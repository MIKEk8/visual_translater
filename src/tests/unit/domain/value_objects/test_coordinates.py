"""
Tests for ScreenCoordinates value object.
"""

import pytest

from src.domain.value_objects.coordinates import ScreenCoordinates


class TestScreenCoordinates:
    """Test ScreenCoordinates value object."""

    def test_coordinates_creation_valid(self):
        """Test creating valid coordinates."""
        coords = ScreenCoordinates(10, 20, 100, 150)
        assert coords.x1 == 10
        assert coords.y1 == 20
        assert coords.x2 == 100
        assert coords.y2 == 150

    def test_coordinates_properties(self):
        """Test coordinate properties calculation."""
        coords = ScreenCoordinates(10, 20, 100, 150)
        assert coords.width == 90
        assert coords.height == 130
        assert coords.area == 11700
        assert coords.center == (55, 85)

    def test_coordinates_negative_values(self):
        """Test creating coordinates with negative values."""
        with pytest.raises(ValueError, match="Coordinates cannot be negative"):
            ScreenCoordinates(-10, 20, 100, 150)

        with pytest.raises(ValueError, match="Coordinates cannot be negative"):
            ScreenCoordinates(10, -20, 100, 150)

    def test_coordinates_invalid_rectangle_x(self):
        """Test creating coordinates with invalid x rectangle."""
        with pytest.raises(ValueError, match="Invalid rectangle: x2/y2 must be greater than x1/y1"):
            ScreenCoordinates(100, 20, 50, 150)  # x2 < x1

    def test_coordinates_invalid_rectangle_y(self):
        """Test creating coordinates with invalid y rectangle."""
        with pytest.raises(ValueError, match="Invalid rectangle: x2/y2 must be greater than x1/y1"):
            ScreenCoordinates(10, 150, 100, 50)  # y2 < y1

    def test_coordinates_equal_values(self):
        """Test creating coordinates with equal values."""
        with pytest.raises(ValueError, match="Invalid rectangle: x2/y2 must be greater than x1/y1"):
            ScreenCoordinates(10, 20, 10, 150)  # x1 == x2

    def test_contains_point_inside(self):
        """Test point containment - inside rectangle."""
        coords = ScreenCoordinates(10, 20, 100, 150)
        assert coords.contains(50, 75) is True
        assert coords.contains(10, 20) is True  # Edge case
        assert coords.contains(100, 150) is True  # Edge case

    def test_contains_point_outside(self):
        """Test point containment - outside rectangle."""
        coords = ScreenCoordinates(10, 20, 100, 150)
        assert coords.contains(5, 75) is False  # Left
        assert coords.contains(105, 75) is False  # Right
        assert coords.contains(50, 15) is False  # Above
        assert coords.contains(50, 155) is False  # Below

    def test_intersects_overlapping(self):
        """Test rectangle intersection - overlapping rectangles."""
        rect1 = ScreenCoordinates(10, 20, 100, 150)
        rect2 = ScreenCoordinates(50, 100, 200, 250)
        assert rect1.intersects(rect2) is True
        assert rect2.intersects(rect1) is True

    def test_intersects_separate(self):
        """Test rectangle intersection - separate rectangles."""
        rect1 = ScreenCoordinates(10, 20, 100, 150)
        rect2 = ScreenCoordinates(200, 200, 300, 350)
        assert rect1.intersects(rect2) is False
        assert rect2.intersects(rect1) is False

    def test_intersects_touching(self):
        """Test rectangle intersection - touching rectangles."""
        rect1 = ScreenCoordinates(10, 20, 100, 150)
        rect2 = ScreenCoordinates(100, 150, 200, 250)
        # Touching at corner - should not intersect (boundaries not included)
        assert rect1.intersects(rect2) is False

    def test_coordinates_immutability(self):
        """Test that coordinates are immutable."""
        coords = ScreenCoordinates(10, 20, 100, 150)
        with pytest.raises(AttributeError):
            coords.x1 = 50  # Should fail - frozen dataclass
