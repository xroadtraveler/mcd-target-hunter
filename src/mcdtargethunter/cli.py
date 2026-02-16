import argparse
import os


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="mcdtargethunter",
        description="MCD Target Hunter (GUI + headless core runner).",
    )
    sub = parser.add_subparsers(dest="cmd", required=False)

    # GUI (default)
    sub.add_parser("gui", help="Launch the GUI (default).")

    # Core / headless runner
    p_core = sub.add_parser("core", help="Run scan + CSV report without GUI.")
    p_core.add_argument("-i", "--input", required=True, help="Path to MCD output file to scan.")
    p_core.add_argument("-o", "--outdir", required=True, help="Folder to write the CSV report into.")
    p_core.add_argument("--target", default=None, help="Target (child) search text.")
    p_core.add_argument("--parent", default=None, help="Parent search text.")
    p_core.add_argument("--no-parent", action="store_true", help="Disable parent lookup.")
    p_core.add_argument("--opno", default=None, help="Operation number search text.")
    p_core.add_argument("--toolchg", default=None, help="Tool change search text.")
    p_core.add_argument("--case", action="store_true", help="Case sensitive search.")
    p_core.add_argument("--print-report-path", action="store_true", help="Print the report path after writing.")

    args = parser.parse_args(argv)

    # Default: GUI
    if args.cmd in (None, "gui"):
        from .mcd_target_hunter_gui import main as gui_main
        gui_main()  # GUI calls sys.exit internally; that’s fine for a desktop app.
        return 0

    if args.cmd == "core":
        from .mcd_hunter_core import (
            AppConfig,
            scan_file_for_hits,
            default_csv_report_path_in_dir,
            write_csv_report,
        )

        input_path = os.path.abspath(args.input)
        outdir = os.path.abspath(args.outdir)

        if not os.path.isfile(input_path):
            raise SystemExit(f"Input file not found: {input_path}")
        if not os.path.isdir(outdir):
            raise SystemExit(f"Output directory not found: {outdir}")

        # Use defaults from config, but allow CLI overrides
        cfg = AppConfig.load()

        target_text = args.target if args.target is not None else cfg.target_text
        parent_text = args.parent if args.parent is not None else cfg.parent_text
        use_parent = False if args.no_parent else cfg.use_parent
        op_no_text = args.opno if args.opno is not None else cfg.op_no_text
        tool_change_text = args.toolchg if args.toolchg is not None else cfg.tool_change_text
        case_sensitive = True if args.case else cfg.case_sensitive

        if not target_text:
            raise SystemExit("Target text cannot be blank (use --target or set it in config).")

        rows, total_hits = scan_file_for_hits(
            input_path,
            target_text,
            parent_text,
            use_parent,
            op_no_text,
            tool_change_text,
            case_sensitive,
        )

        report_path = default_csv_report_path_in_dir(input_path, outdir)
        write_csv_report(report_path, rows, total_hits)

        if args.print_report_path:
            print(report_path)

        print(f"Complete. Report created: {report_path}")
        print(f"Total hits: {total_hits}")
        return 0

    return 0
