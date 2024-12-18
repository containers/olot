import pytest


def pytest_collection_modifyitems(config, items):
    for item in items:
        skip_e2e_skopeo = pytest.mark.skip(
            reason="this is an end-to-end test, requires explicit opt-in --e2e-skopeo option to run."
        )
        skip_not_e2e = pytest.mark.skip(
            reason="skipping non-e2e tests; opt-out of --e2e -like options to run."
        )
        if "e2e_skopeo" in item.keywords:
            if not config.getoption("--e2e-skopeo"):
                item.add_marker(skip_e2e_skopeo)
            continue
        # elif "e2e_model_registry" in item.keywords:
        #     if not config.getoption("--e2e-model-registry"):
        #         item.add_marker(skip_e2e_model_registry)
        #     continue

        if config.getoption("--e2e-skopeo"): # or config.getoption("--e2e-model-registry"):
            item.add_marker(skip_not_e2e)


def pytest_addoption(parser):
    parser.addoption(
        "--e2e-skopeo",
        action="store_true",
        default=False,
        help="opt-in to run tests marked with e2e_skopeo",
    )
