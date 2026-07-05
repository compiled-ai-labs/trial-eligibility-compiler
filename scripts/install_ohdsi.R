#!/usr/bin/env Rscript
# Pinned install of the OHDSI runtime stack + duckdb driver.
#
# Versions are pinned for determinism (PLAN.md §10). In the devcontainer this is
# snapshotted into renv.lock via renv::snapshot(); CI runs this script directly so
# the same versions are used everywhere.

options(warn = 2)  # treat install warnings as errors

repos <- c(CRAN = "https://cloud.r-project.org")
install_pinned <- function(pkg, version) {
  if (!requireNamespace("remotes", quietly = TRUE)) {
    install.packages("remotes", repos = repos)
  }
  remotes::install_version(pkg, version = version, repos = repos, upgrade = "never")
}

# duckdb DBI driver (DatabaseConnector talks to it via DBI)
install_pinned("duckdb", "1.1.3")

# OHDSI runtime — the ONLY thing that builds/executes cohort SQL
install_pinned("SqlRender", "1.19.1")
install_pinned("DatabaseConnector", "6.3.2")
install_pinned("CirceR", "1.3.4")
install_pinned("jsonlite", "1.8.9")

cat("OHDSI stack installed:\n")
for (p in c("duckdb", "SqlRender", "DatabaseConnector", "CirceR", "jsonlite")) {
  cat(sprintf("  %s %s\n", p, as.character(packageVersion(p))))
}
