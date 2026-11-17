from pathlib import Path

from simulator.container_metadata import (
    DEFAULT_METADATA_PATH,
    get_container_metadata,
    load_container_metadata,
)

from simulator.product_reference import (
    DEFAULT_PRODUCT_REFERENCE_PATH,
    find_product_reference,
    load_product_references,
)


def load_product_references_for_containers(
    containers,
    metadata_path=None,
    product_reference_path=None,
):
    """
    Match every active container to its product reference.

    If neither reference CSV exists, return an empty mapping
    to preserve generic simulation mode.

    If only one CSV exists, raise an error rather than silently
    running a partially configured simulation.
    """

    metadata_file = (
        Path(metadata_path)
        if metadata_path is not None
        else DEFAULT_METADATA_PATH
    )

    product_file = (
        Path(product_reference_path)
        if product_reference_path is not None
        else DEFAULT_PRODUCT_REFERENCE_PATH
    )

    metadata_exists = metadata_file.is_file()
    product_exists = product_file.is_file()

    # Preserve generic simulation when neither dataset is available.
    if not metadata_exists and not product_exists:
        return {}

    # Do not allow partial reference-data configuration.
    if not metadata_exists:
        raise FileNotFoundError(
            f"Container metadata CSV not found: {metadata_file}"
        )

    if not product_exists:
        raise FileNotFoundError(
            f"Product reference CSV not found: {product_file}"
        )

    metadata = load_container_metadata(metadata_file)
    product_references = load_product_references(product_file)

    container_references = {}

    for container_id in containers:

        container = get_container_metadata(
            metadata,
            container_id,
        )

        reference = find_product_reference(
            product_references,
            container.product_name,
        )

        container_references[container_id] = reference

    return container_references