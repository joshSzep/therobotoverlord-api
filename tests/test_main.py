from therobotoverlord_api.main import main


def test_main() -> None:
    """Test the main function."""
    app = main()  # Should not raise any exceptions
    assert app is not None
    assert app.title == "The Robot Overlord API"
