from cpython.__main__ import configure_logger, main, parse_args

cmd, cmd_kwargs, verbosity, traceback_cm = parse_args()
configure_logger(verbosity)
with traceback_cm:
    main(cmd, cmd_kwargs)
