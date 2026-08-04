from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def read_csv_safely(path: Path) -> pd.DataFrame:
    """
    Read a CSV while allowing pandas to detect comma or semicolon separators.
    Tries common encodings used by Spanish data portals.
    """
    errors: list[str] = []

    for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            return pd.read_csv(
                path,
                sep=None,
                engine="python",
                encoding=encoding,
            )
        except Exception as exc:
            errors.append(f"{encoding}: {exc}")

    raise ValueError(
        f"Could not read {path}\n" + "\n".join(errors)
    )


def merge_csv_folder(
    input_folder: Path,
    output_file: Path,
    recursive: bool = True,
) -> pd.DataFrame:
    """
    Merge CSV files with the same structure.

    Raw files are not modified.
    Duplicate rows are reported but not silently removed.
    """
    pattern = "**/*.csv" if recursive else "*.csv"
    csv_files = sorted(input_folder.glob(pattern))

    # Prevent an existing merged output from being read again.
    csv_files = [
        path for path in csv_files
        if path.resolve() != output_file.resolve()
    ]

    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in {input_folder}"
        )

    frames: list[pd.DataFrame] = []
    reference_columns: list[str] | None = None

    for path in csv_files:
        print(f"Reading: {path}")

        frame = read_csv_safely(path)
        frame.columns = [str(column).strip() for column in frame.columns]

        if reference_columns is None:
            reference_columns = list(frame.columns)
        elif list(frame.columns) != reference_columns:
            missing = sorted(set(reference_columns) - set(frame.columns))
            extra = sorted(set(frame.columns) - set(reference_columns))

            raise ValueError(
                f"Column mismatch in {path}\n"
                f"Missing columns: {missing}\n"
                f"Extra columns: {extra}"
            )

        frame["source_file"] = path.name
        frame["source_relative_path"] = str(
            path.relative_to(input_folder)
        )

        frames.append(frame)

    merged = pd.concat(frames, ignore_index=True)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_file, index=False, encoding="utf-8-sig")

    duplicate_count = int(
        merged.drop(
            columns=["source_file", "source_relative_path"],
            errors="ignore",
        ).duplicated().sum()
    )

    print()
    print(f"Files merged: {len(csv_files)}")
    print(f"Rows written: {len(merged):,}")
    print(f"Possible duplicate rows: {duplicate_count:,}")
    print(f"Output: {output_file}")

    return merged


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge CSV files from one dataset folder."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Folder containing the source CSV files.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path for the merged CSV file.",
    )
    parser.add_argument(
        "--non-recursive",
        action="store_true",
        help="Search only the top-level input folder.",
    )

    args = parser.parse_args()

    merge_csv_folder(
        input_folder=Path(args.input),
        output_file=Path(args.output),
        recursive=not args.non_recursive,
    )


if __name__ == "__main__":
    main()
