import asyncio

from callus_research.services.batch_runner import (
    export_results_bundle,
    load_targets,
    run_targets,
)


async def main():
    targets = load_targets()
    results = await run_targets(
        targets,
        progress_callback=lambda _, __, target: print(
            f"Processing: {target.university_name} | {target.program_name}"
        ),
    )

    export_paths = export_results_bundle(results)

    print(f"Saved target results: {export_paths['target_results']}")
    print(f"Saved final records: {export_paths['final_records']}")
    print(f"Saved comparison CSV: {export_paths['comparison_csv']}")


if __name__ == "__main__":
    asyncio.run(main())
