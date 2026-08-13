


def test_fixture_available(mock_sr_tags_config):
    import os
    assert os.path.exists(mock_sr_tags_config)
    print(f"Config file exists at: {mock_sr_tags_config}")


