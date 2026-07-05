#!/usr/bin/env Rscript
# OHDSI execution bridge (Part 5).
#
# Executes a committed cohort.json against a one-person duckdb OMOP CDM using ONLY
# standard OHDSI packages. No cohort SQL is hand-written here: CirceR builds the
# query, SqlRender translates it to the duckdb dialect, DatabaseConnector runs it
# with inclusion-rule statistics enabled. Emits JSON to stdout between markers.
#
# Usage: Rscript ohdsi_bridge.R <cohort.json> <cdm.duckdb>
#
# Contract (stdout, between the markers):
#   {"membership": <bool>,
#    "rules": [{"rule_sequence": <int>, "name": <str>, "satisfied": <bool>}, ...]}

suppressWarnings(suppressMessages({
  library(CirceR)
  library(SqlRender)
  library(DatabaseConnector)
  library(jsonlite)
}))

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) stop("usage: ohdsi_bridge.R <cohort.json> <cdm.duckdb>")
cohortJsonPath <- args[[1]]
duckdbPath <- args[[2]]

cohortJson <- paste(readLines(cohortJsonPath, warn = FALSE), collapse = "\n")

# 1. Circe builds the cohort SQL (with inclusion-rule stats).
expr <- CirceR::cohortExpressionFromJson(cohortJson)
genOptions <- CirceR::createGenerateOptions(generateStats = TRUE)
sql <- CirceR::buildCohortQuery(expr, genOptions)

# 2. Render our schema/table names, then translate to duckdb.
sql <- SqlRender::render(
  sql,
  cdm_database_schema = "main",
  vocabulary_database_schema = "main",
  target_database_schema = "main",
  results_database_schema = "main",
  target_cohort_table = "cohort",
  target_cohort_id = 1L,
  warnOnMissingParameters = FALSE
)
sql <- SqlRender::translate(sql, targetDialect = "duckdb")

# 3. Connect to the synthetic duckdb CDM.
connectionDetails <- DatabaseConnector::createConnectionDetails(
  dbms = "duckdb", server = duckdbPath
)
con <- DatabaseConnector::connect(connectionDetails)
on.exit(DatabaseConnector::disconnect(con), add = TRUE)

# 4. Result tables Circe's stats SQL writes into (standard OHDSI result schema).
resultDDL <- "
DROP TABLE IF EXISTS cohort;
CREATE TABLE cohort (cohort_definition_id BIGINT, subject_id BIGINT, cohort_start_date DATE, cohort_end_date DATE);
DROP TABLE IF EXISTS cohort_inclusion;
CREATE TABLE cohort_inclusion (cohort_definition_id BIGINT, rule_sequence INT, name VARCHAR, description VARCHAR);
DROP TABLE IF EXISTS cohort_inclusion_result;
CREATE TABLE cohort_inclusion_result (cohort_definition_id BIGINT, inclusion_rule_mask INT, person_count BIGINT, mode_id INT);
DROP TABLE IF EXISTS cohort_inclusion_stats;
CREATE TABLE cohort_inclusion_stats (cohort_definition_id BIGINT, rule_sequence INT, person_count BIGINT, gain_count BIGINT, person_total BIGINT, mode_id INT);
DROP TABLE IF EXISTS cohort_summary_stats;
CREATE TABLE cohort_summary_stats (cohort_definition_id BIGINT, base_count BIGINT, final_count BIGINT, mode_id INT);
DROP TABLE IF EXISTS cohort_censor_stats;
CREATE TABLE cohort_censor_stats (cohort_definition_id BIGINT, lost_count BIGINT);
"
DatabaseConnector::executeSql(con, SqlRender::translate(resultDDL, targetDialect = "duckdb"),
                              progressBar = FALSE, reportOverallTime = FALSE)

# cohort_inclusion (rule metadata) is populated from the expression, not the
# generated SQL. Insert one row per named inclusion rule, 0-indexed sequence.
parsed <- jsonlite::fromJSON(cohortJson, simplifyVector = FALSE)
ruleNames <- vapply(parsed$InclusionRules, function(r) r$name, character(1))
for (i in seq_along(ruleNames)) {
  DatabaseConnector::executeSql(
    con,
    sprintf("INSERT INTO cohort_inclusion VALUES (1, %d, '%s', '');", i - 1L, ruleNames[[i]]),
    progressBar = FALSE, reportOverallTime = FALSE
  )
}

# 5. Execute the cohort + stats SQL.
DatabaseConnector::executeSql(con, sql, progressBar = FALSE, reportOverallTime = FALSE)

# 6. Read back membership and the satisfied-rule bitmask for our single subject.
inCohort <- DatabaseConnector::querySql(
  con, "SELECT COUNT(*) AS n FROM cohort WHERE subject_id = 1;"
)$N[[1]]
membership <- inCohort > 0

maskRows <- DatabaseConnector::querySql(
  con,
  "SELECT inclusion_rule_mask AS mask, person_count AS pc
     FROM cohort_inclusion_result
    WHERE cohort_definition_id = 1 AND mode_id = 0
    ORDER BY person_count DESC;"
)
mask <- if (nrow(maskRows) == 0) 0L else as.integer(maskRows$MASK[[1]])

rules <- lapply(seq_along(ruleNames), function(i) {
  bit <- bitwShiftL(1L, i - 1L)
  list(rule_sequence = i - 1L,
       name = ruleNames[[i]],
       satisfied = bitwAnd(mask, bit) != 0L)
})

cat("<<<TRCHECK_JSON>>>\n")
cat(jsonlite::toJSON(list(membership = membership, rules = rules),
                     auto_unbox = TRUE, pretty = FALSE))
cat("\n<<<END_TRCHECK_JSON>>>\n")
