import logging

root = logging.getLogger()
root.setLevel(logging.DEBUG)

fmt = logging.Formatter("[%(asctime)s — %(name)s — %(levelname)s] %(message)s")

dbg_file_logger = logging.FileHandler("dbg.log")
dbg_file_logger.setLevel(logging.DEBUG)
dbg_file_logger.setFormatter(fmt)

info_file_logger = logging.FileHandler("log.log")
info_file_logger.setLevel(logging.INFO)
info_file_logger.setFormatter(fmt)

out_logger = logging.StreamHandler()
out_logger.setLevel(logging.INFO)
out_logger.setFormatter(fmt)

root.addHandler(dbg_file_logger)
root.addHandler(info_file_logger)
root.addHandler(out_logger)

if __name__ == "__main__":
    LOG = logging.getLogger("logpy")

    LOG.debug("hej debug")
    LOG.info("hej info")
    LOG.warning("hej warning")
    LOG.error("hej error")
    LOG.critical("hej critical")
