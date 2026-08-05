# Phase 0.5 Audit Report — PEARL-Neuro (ds004796)

**Generated:** 2026-08-05 | **Run:** 20260805T175341Z-d891d70

## Verdict: PROCEED

PROCEED: all 79 analysis-cohort subjects reconcile to the client's groups (0 blocking statuses). The dataset holds 192 genotyped participants; only the 79 in the client list are expected to have imaging. sub-69 is not among the genotyped participants, which closes the Phase 0 question. No blocking confounds detected. Phase 1 may proceed under the download plan in §5.

---

## 0. Cohort Definition

The dataset contains **192 genotyped participants**; of these,
**79** are in the client's imaging cohort (the client list of 79).
The remaining **113** are genetic-only. Everything downstream
filters on `final_include` in `cohort_definition.csv`.

| Subject | In client list | In participants.tsv | Has EEG | Final include |
|---------|----------------|---------------------|---------|---------------|
| sub-01 | True | True | True | True |
| sub-02 | True | True | True | True |
| sub-03 | True | True | True | True |
| sub-04 | True | True | True | True |
| sub-05 | True | True | True | True |
| sub-06 | True | True | True | True |
| sub-07 | True | True | True | True |
| sub-08 | True | True | True | True |
| sub-09 | True | True | True | True |
| sub-10 | True | True | True | True |
| sub-100 | False | True | False | False |
| sub-101 | False | True | False | False |
| sub-102 | False | True | False | False |
| sub-104 | False | True | False | False |
| sub-105 | False | True | False | False |
| sub-106 | False | True | False | False |
| sub-107 | False | True | False | False |
| sub-108 | False | True | False | False |
| sub-109 | False | True | False | False |
| sub-11 | True | True | True | True |
| sub-110 | False | True | False | False |
| sub-112 | False | True | False | False |
| sub-113 | False | True | False | False |
| sub-114 | False | True | False | False |
| sub-115 | False | True | False | False |
| sub-116 | False | True | False | False |
| sub-117 | False | True | False | False |
| sub-118 | False | True | False | False |
| sub-119 | False | True | False | False |
| sub-12 | True | True | True | True |
| sub-120 | False | True | False | False |
| sub-121 | False | True | False | False |
| sub-122 | False | True | False | False |
| sub-123 | False | True | False | False |
| sub-124 | False | True | False | False |
| sub-125 | False | True | False | False |
| sub-126 | False | True | False | False |
| sub-127 | False | True | False | False |
| sub-128 | False | True | False | False |
| sub-129 | False | True | False | False |
| sub-13 | True | True | True | True |
| sub-130 | False | True | False | False |
| sub-131 | False | True | False | False |
| sub-132 | False | True | False | False |
| sub-133 | False | True | False | False |
| sub-134 | False | True | False | False |
| sub-135 | False | True | False | False |
| sub-136 | False | True | False | False |
| sub-137 | False | True | False | False |
| sub-138 | False | True | False | False |
| sub-14 | True | True | True | True |
| sub-140 | False | True | False | False |
| sub-141 | False | True | False | False |
| sub-142 | False | True | False | False |
| sub-143 | False | True | False | False |
| sub-144 | False | True | False | False |
| sub-145 | False | True | False | False |
| sub-146 | False | True | False | False |
| sub-147 | False | True | False | False |
| sub-148 | False | True | False | False |
| sub-149 | False | True | False | False |
| sub-15 | True | True | True | True |
| sub-150 | False | True | False | False |
| sub-151 | False | True | False | False |
| sub-152 | False | True | False | False |
| sub-153 | False | True | False | False |
| sub-155 | False | True | False | False |
| sub-156 | False | True | False | False |
| sub-159 | False | True | False | False |
| sub-16 | True | True | True | True |
| sub-160 | False | True | False | False |
| sub-161 | False | True | False | False |
| sub-162 | False | True | False | False |
| sub-163 | False | True | False | False |
| sub-164 | False | True | False | False |
| sub-165 | False | True | False | False |
| sub-166 | False | True | False | False |
| sub-167 | False | True | False | False |
| sub-168 | False | True | False | False |
| sub-169 | False | True | False | False |
| sub-17 | True | True | True | True |
| sub-171 | False | True | False | False |
| sub-172 | False | True | False | False |
| sub-173 | False | True | False | False |
| sub-174 | False | True | False | False |
| sub-175 | False | True | False | False |
| sub-176 | False | True | False | False |
| sub-177 | False | True | False | False |
| sub-178 | False | True | False | False |
| sub-179 | False | True | False | False |
| sub-18 | True | True | True | True |
| sub-180 | False | True | False | False |
| sub-181 | False | True | False | False |
| sub-182 | False | True | False | False |
| sub-183 | False | True | False | False |
| sub-184 | False | True | False | False |
| sub-185 | False | True | False | False |
| sub-186 | False | True | False | False |
| sub-187 | False | True | False | False |
| sub-188 | False | True | False | False |
| sub-189 | False | True | False | False |
| sub-19 | True | True | True | True |
| sub-190 | False | True | False | False |
| sub-191 | False | True | False | False |
| sub-192 | False | True | False | False |
| sub-193 | False | True | False | False |
| sub-194 | False | True | False | False |
| sub-195 | False | True | False | False |
| sub-196 | False | True | False | False |
| sub-197 | False | True | False | False |
| sub-198 | False | True | False | False |
| sub-199 | False | True | False | False |
| sub-20 | True | True | True | True |
| sub-200 | False | True | False | False |
| sub-21 | True | True | True | True |
| sub-22 | True | True | True | True |
| sub-23 | True | True | True | True |
| sub-24 | True | True | True | True |
| sub-25 | True | True | True | True |
| sub-26 | True | True | True | True |
| sub-27 | True | True | True | True |
| sub-28 | True | True | True | True |
| sub-29 | True | True | True | True |
| sub-30 | True | True | True | True |
| sub-31 | True | True | True | True |
| sub-32 | True | True | True | True |
| sub-33 | True | True | True | True |
| sub-34 | True | True | True | True |
| sub-35 | True | True | True | True |
| sub-36 | True | True | True | True |
| sub-37 | True | True | True | True |
| sub-38 | True | True | True | True |
| sub-39 | True | True | True | True |
| sub-40 | True | True | True | True |
| sub-41 | True | True | True | True |
| sub-42 | True | True | True | True |
| sub-43 | True | True | True | True |
| sub-44 | True | True | True | True |
| sub-45 | True | True | True | True |
| sub-46 | True | True | True | True |
| sub-47 | True | True | True | True |
| sub-48 | True | True | True | True |
| sub-49 | True | True | True | True |
| sub-50 | True | True | True | True |
| sub-51 | True | True | True | True |
| sub-52 | True | True | True | True |
| sub-53 | True | True | True | True |
| sub-54 | True | True | True | True |
| sub-55 | True | True | True | True |
| sub-56 | True | True | True | True |
| sub-57 | True | True | True | True |
| sub-58 | True | True | True | True |
| sub-59 | True | True | True | True |
| sub-60 | True | True | True | True |
| sub-61 | True | True | True | True |
| sub-62 | True | True | True | True |
| sub-63 | True | True | True | True |
| sub-64 | True | True | True | True |
| sub-65 | True | True | True | True |
| sub-66 | True | True | True | True |
| sub-67 | True | True | True | True |
| sub-68 | True | True | True | True |
| sub-70 | True | True | True | True |
| sub-71 | True | True | True | True |
| sub-72 | True | True | True | True |
| sub-73 | True | True | True | True |
| sub-74 | True | True | True | True |
| sub-75 | True | True | True | True |
| sub-76 | True | True | True | True |
| sub-77 | True | True | True | True |
| sub-78 | True | True | True | True |
| sub-79 | True | True | True | True |
| sub-80 | True | True | True | True |
| sub-81 | False | True | False | False |
| sub-82 | False | True | False | False |
| sub-83 | False | True | False | False |
| sub-84 | False | True | False | False |
| sub-85 | False | True | False | False |
| sub-86 | False | True | False | False |
| sub-87 | False | True | False | False |
| sub-88 | False | True | False | False |
| sub-89 | False | True | False | False |
| sub-90 | False | True | False | False |
| sub-91 | False | True | False | False |
| sub-92 | False | True | False | False |
| sub-93 | False | True | False | False |
| sub-94 | False | True | False | False |
| sub-95 | False | True | False | False |
| sub-96 | False | True | False | False |
| sub-97 | False | True | False | False |
| sub-98 | False | True | False | False |
| sub-99 | False | True | False | False |

## 1. Dataset Provenance

| Field | Value |
|-------|-------|
| Accession | ds004796 |
| Version | v1.0.0 |
| Version source | DOI |
| Fetch date | 2026-08-05 |
| participants.tsv SHA-256 | 909d8736a138a2d3… |
| S3 listing date | 2026-08-05 |
| Total downloaded bytes | 72,491 |
| Files downloaded | 5 |

## 2. Group Reconciliation

| Subject | APOE raw | PICALM raw | APOE norm | PICALM norm | Derived | Client | Status |
|---------|----------|------------|-----------|-------------|---------|--------|--------|
| sub-01 | e3/e3 | A/A | 3/3 | AA | N | N | RECONCILED |
| sub-02 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-03 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-04 | e3/e3 | A/A | 3/3 | AA | N | N | RECONCILED |
| sub-05 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-06 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-07 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-08 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-09 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-10 | e3/e3 | A/A | 3/3 | AA | N | N | RECONCILED |
| sub-100 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-101 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-102 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-104 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-105 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-106 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-107 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-108 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-109 | e3/e3 | A/A | 3/3 | AA | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-11 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-110 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-112 | e3/e2 | A/A | 3/2 | AA | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-113 | e3/e3 | A/A | 3/3 | AA | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-114 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-115 | e3/e2 | G/G | 3/2 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-116 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-117 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-118 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-119 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-12 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-120 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-121 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-122 | e3/e2 | G/A | 3/2 | AG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-123 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-124 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-125 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-126 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-127 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-128 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-129 | e3/e2 | G/G | 3/2 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-13 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-130 | e3/e2 | G/G | 3/2 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-131 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-132 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-133 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-134 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-135 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-136 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-137 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-138 | e3/e2 | G/G | 3/2 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-14 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-140 | e3/e3 | G/A  | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-141 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-142 | e2/e4 | G/G | 2/4 | GG | A_P_plus | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-143 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-144 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-145 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-146 | e3/e2 | G/G | 3/2 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-147 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-148 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-149 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-15 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-150 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-151 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-152 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-153 | e3/e2 | G/A | 3/2 | AG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-155 | e2/e2 | G/G | 2/2 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-156 | e3/e2 | G/G | 3/2 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-159 | e3/e2 | G/G | 3/2 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-16 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-160 | e2/e4 | G/A | 2/4 | AG | A_P_minus | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-161 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-162 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-163 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-164 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-165 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-166 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-167 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-168 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-169 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-17 | e3/e3 | A/A | 3/3 | AA | N | N | RECONCILED |
| sub-171 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-172 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-173 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-174 | e3/e2 | G/A | 3/2 | AG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-175 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-176 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-177 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-178 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-179 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-18 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-180 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-181 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-182 | e3/e2  | G/A | 3/2 | AG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-183 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-184 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-185 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-186 | e3/e2 | G/A | 3/2 | AG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-187 | e3/e2  | G/G | 3/2 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-188 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-189 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-19 | e3/e3 | A/A | 3/3 | AA | N | N | RECONCILED |
| sub-190 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-191 | e3/e2 | G/A | 3/2 | AG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-192 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-193 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-194 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-195 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-196 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-197 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-198 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-199 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-20 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-200 | e3/e2 | G/A | 3/2 | AG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-21 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-22 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-23 | e3/e3 | A/A | 3/3 | AA | N | N | RECONCILED |
| sub-24 | e3/e3 | A/A | 3/3 | AA | N | N | RECONCILED |
| sub-25 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-26 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-27 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-28 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-29 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-30 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-31 | e3/e3 | G/A | 3/3 | AG | N | N | RECONCILED |
| sub-32 | e3/e4 | G/G | 3/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-33 | e4/e4 | G/G | 4/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-34 | e3/e4 | G/G | 3/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-35 | e3/e4 | G/G | 3/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-36 | e3/e4 | G/G | 3/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-37 | e3/e4 | G/G | 3/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-38 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-39 | e3/e4 | G/G | 3/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-40 | e3/e4 | G/G | 3/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-41 | e4/e4 | G/G | 4/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-42 | e3/e4 | G/G | 3/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-43 | e3/e4 | G/G | 3/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-44 | e3/e4 | G/G | 3/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-45 | e3/e4 | G/G | 3/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-46 | e2/e4 | G/G | 2/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-47 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-48 | e3/e4 | G/G | 3/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-49 | e3/e4 | G/G | 3/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-50 | e3/e4 | G/G | 3/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-51 | e3/e4 | G/G | 3/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-52 | e3/e4 | G/G | 3/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-53 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-54 | e3/e4 | G/G | 3/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-55 | e3/e4 | G/G | 3/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-56 | e3/e4 | G/G | 3/4 | GG | A_P_plus | A_P_plus | RECONCILED |
| sub-57 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-58 | e3/e4 | A/A | 3/4 | AA | A_P_minus | A_P_minus | RECONCILED |
| sub-59 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-60 | e3/e4 | A/A | 3/4 | AA | A_P_minus | A_P_minus | RECONCILED |
| sub-61 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-62 | e3/e4 | A/A | 3/4 | AA | A_P_minus | A_P_minus | RECONCILED |
| sub-63 | e3/e4 | A/A | 3/4 | AA | A_P_minus | A_P_minus | RECONCILED |
| sub-64 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-65 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-66 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-67 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-68 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-70 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-71 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-72 | e3/e4 | G/A  | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-73 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-74 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-75 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-76 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-77 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-78 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-79 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-80 | e3/e4 | G/A | 3/4 | AG | A_P_minus | A_P_minus | RECONCILED |
| sub-81 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-82 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-83 | e3/e4 | G/A | 3/4 | AG | A_P_minus | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-84 | e3/e3 | A/A | 3/3 | AA | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-85 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-86 | e3/e2 | G/A | 3/2 | AG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-87 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-88 | e3/e2 | G/A | 3/2 | AG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-89 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-90 | e3/e2 | G/G | 3/2 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-91 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-92 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-93 | e3/e3 | G/A  | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-94 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-95 | e3/e3 | G/G | 3/3 | GG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-96 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-97 | e3/e3 | G/A | 3/3 | AG | N | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-98 | e3/e2 | G/A | 3/2 | AG | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |
| sub-99 | e3/e2 | A/A | 3/2 | AA | UNRESOLVABLE | NOT_IN_CLIENT_LIST | GENETIC_COHORT_ONLY |

### Discrepancy Summary

- **Blocking statuses (MISMATCH + MISSING_FROM_TSV):** 0
- Missing from TSV: none
- **sub-69:** absent from participants.tsv — not one of the 192 genotyped participants
- e4/e4 homozygotes in A_P_plus: 2 (claimed: 2)

## 3. EEG Inventory & Effective N

### Effective N per task (wide)

| Task | N | A_P_minus | A_P_plus | Total |
|------|---|-----------|----------|-------|
| msit | 31 | 26 | 22 | 79 |
| rest | 31 | 26 | 21 | 78 |
| sternberg | 31 | 26 | 21 | 78 |

### Missingness per task/group

| Task | Group | N total | Have data | Missing | Missing subjects | Test | p |
|------|-------|---------|-----------|---------|------------------|------|---|
| msit | N | 31 | 31 | 0 |  | n/a (degenerate table) | nan |
| msit | A_P_minus | 26 | 26 | 0 |  | n/a (degenerate table) | nan |
| msit | A_P_plus | 22 | 22 | 0 |  | n/a (degenerate table) | nan |
| rest | N | 31 | 31 | 0 |  | chi-square (missing × group) | 0.269264 |
| rest | A_P_minus | 26 | 26 | 0 |  | chi-square (missing × group) | 0.269264 |
| rest | A_P_plus | 22 | 21 | 1 | sub-55 | chi-square (missing × group) | 0.269264 |
| sternberg | N | 31 | 31 | 0 |  | chi-square (missing × group) | 0.269264 |
| sternberg | A_P_minus | 26 | 26 | 0 |  | chi-square (missing × group) | 0.269264 |
| sternberg | A_P_plus | 22 | 21 | 1 | sub-51 | chi-square (missing × group) | 0.269264 |

**Documented missingness verification:** sub-51 (sternberg) actually missing = True; sub-55 (rest) actually missing = True.

## 4. Confound Analysis

| Framing | Variable | Test | p | Effect | Measure | Verdict | Mitigation |
|---------|----------|------|---|--------|---------|---------|------------|
| multiclass_3 | age | Kruskal-Wallis | 0.480279 | -0.007 | eta-squared | CLEAR |  |
| multiclass_3 | BMI | Kruskal-Wallis | 0.414508 | -0.0031 | eta-squared | CLEAR |  |
| multiclass_3 | SES | Kruskal-Wallis | 0.092276 | 0.0364 | eta-squared | WATCH | Consider including SES as covariate in Phase 3 models |
| multiclass_3 | EHI | Kruskal-Wallis | 0.701495 | -0.017 | eta-squared | CLEAR |  |
| multiclass_3 | BDI | Kruskal-Wallis | 0.061058 | 0.0473 | eta-squared | WATCH | Consider including BDI as covariate in Phase 3 models |
| multiclass_3 | RPM | Kruskal-Wallis | 0.631558 | -0.0142 | eta-squared | CLEAR |  |
| multiclass_3 | leukocytes | Kruskal-Wallis | 0.499085 | -0.0084 | eta-squared | CLEAR |  |
| multiclass_3 | hemoglobin | Kruskal-Wallis | 0.714464 | -0.0182 | eta-squared | CLEAR |  |
| multiclass_3 | cholesterol_HDL | Kruskal-Wallis | 0.444728 | -0.0052 | eta-squared | CLEAR |  |
| multiclass_3 | LDL_cholesterol | Kruskal-Wallis | 0.858113 | -0.0232 | eta-squared | CLEAR |  |
| multiclass_3 | triglycerides | Kruskal-Wallis | 0.258392 | 0.0097 | eta-squared | CLEAR |  |
| multiclass_3 | sex | chi-square (low expected counts) | 0.904182 | 0.0505 | Cramers V | CLEAR |  |
| multiclass_3 | education | chi-square (low expected counts) | 0.458761 | 0.226 | Cramers V | CLEAR |  |
| multiclass_3 | education | Spearman (education × group order) | 0.302096 | 0.1242 | Spearman rho | CLEAR |  |
| multiclass_3 | smoking_status | chi-square (low expected counts) | 0.229981 | 0.2683 | Cramers V | CLEAR |  |
| multiclass_3 | dementia_history_parents | chi-square (low expected counts) | 0.174658 | 0.2835 | Cramers V | CLEAR |  |
| binary_risk_vs_none | age | Kruskal-Wallis | 0.2333 | 0.0055 | eta-squared | CLEAR |  |
| binary_risk_vs_none | BMI | Kruskal-Wallis | 0.427659 | -0.0048 | eta-squared | CLEAR |  |
| binary_risk_vs_none | SES | Kruskal-Wallis | 0.104706 | 0.0212 | eta-squared | CLEAR |  |
| binary_risk_vs_none | EHI | Kruskal-Wallis | 0.56036 | -0.0086 | eta-squared | CLEAR |  |
| binary_risk_vs_none | BDI | Kruskal-Wallis | 0.040205 | 0.0417 | eta-squared | WATCH | Consider including BDI as covariate in Phase 3 models |
| binary_risk_vs_none | RPM | Kruskal-Wallis | 0.340907 | -0.0012 | eta-squared | CLEAR |  |
| binary_risk_vs_none | leukocytes | Kruskal-Wallis | 0.23842 | 0.0053 | eta-squared | CLEAR |  |
| binary_risk_vs_none | hemoglobin | Kruskal-Wallis | 0.894819 | -0.0133 | eta-squared | CLEAR |  |
| binary_risk_vs_none | cholesterol_HDL | Kruskal-Wallis | 0.962063 | -0.0135 | eta-squared | CLEAR |  |
| binary_risk_vs_none | LDL_cholesterol | Kruskal-Wallis | 0.731214 | -0.0119 | eta-squared | CLEAR |  |
| binary_risk_vs_none | triglycerides | Kruskal-Wallis | 0.366155 | -0.0025 | eta-squared | CLEAR |  |
| binary_risk_vs_none | sex | Fisher's exact | 0.819701 | 0.0361 | rank-biserial r | CLEAR |  |
| binary_risk_vs_none | education | chi-square (low expected counts) | 0.614319 | 0.1172 | Cramers V | CLEAR |  |
| binary_risk_vs_none | smoking_status | chi-square (low expected counts) | 0.336033 | 0.1672 | Cramers V | CLEAR |  |
| binary_risk_vs_none | dementia_history_parents | chi-square (low expected counts) | 0.229833 | 0.1929 | Cramers V | CLEAR |  |
| binary_high_vs_rest | age | Kruskal-Wallis | 0.434678 | -0.0051 | eta-squared | CLEAR |  |
| binary_high_vs_rest | BMI | Kruskal-Wallis | 0.187522 | 0.0096 | eta-squared | CLEAR |  |
| binary_high_vs_rest | SES | Kruskal-Wallis | 0.648705 | -0.0103 | eta-squared | CLEAR |  |
| binary_high_vs_rest | EHI | Kruskal-Wallis | 0.81319 | -0.0123 | eta-squared | CLEAR |  |
| binary_high_vs_rest | BDI | Kruskal-Wallis | 0.995619 | -0.013 | eta-squared | CLEAR |  |
| binary_high_vs_rest | RPM | Kruskal-Wallis | 0.568093 | -0.0088 | eta-squared | CLEAR |  |
| binary_high_vs_rest | leukocytes | Kruskal-Wallis | 0.536104 | -0.0083 | eta-squared | CLEAR |  |
| binary_high_vs_rest | hemoglobin | Kruskal-Wallis | 0.449385 | -0.0058 | eta-squared | CLEAR |  |
| binary_high_vs_rest | cholesterol_HDL | Kruskal-Wallis | 0.291998 | 0.0015 | eta-squared | CLEAR |  |
| binary_high_vs_rest | LDL_cholesterol | Kruskal-Wallis | 0.58248 | -0.0094 | eta-squared | CLEAR |  |
| binary_high_vs_rest | triglycerides | Kruskal-Wallis | 0.491952 | -0.0071 | eta-squared | CLEAR |  |
| binary_high_vs_rest | sex | Fisher's exact | 0.802707 | 0.0486 | rank-biserial r | CLEAR |  |
| binary_high_vs_rest | education | chi-square (low expected counts) | 0.248271 | 0.1981 | Cramers V | CLEAR |  |
| binary_high_vs_rest | smoking_status | chi-square (low expected counts) | 0.668807 | 0.1016 | Cramers V | CLEAR |  |
| binary_high_vs_rest | dementia_history_parents | chi-square (low expected counts) | 0.258655 | 0.185 | Cramers V | CLEAR |  |

## 5. Phase 1 Download Plan

| Scope | Raw GB | Derivatives GB | Total GB | Fits in 95 GB? |
|---|---|---|---|---|
| A_full_eeg | 75.87 | 66.98 | 142.85 | NO |
| B_rest_msit | 46.47 | 40.93 | 87.4 | YES |
| C_rest_msit_only | 46.47 | 40.93 | 87.4 | YES |

**Recommendation:** C_rest_msit_only

Manifest: `D:\younes\AI-zhaimer\pearl\data\derivatives\phase0\.tmp-20260805T175341Z-d891d70\phase1_manifest.csv` — *nothing downloaded; approval required.*

## 6. Open Questions & Assumptions

- Genotype columns resolved from participants.tsv schema and persisted in config/audit.yaml (no heuristics).
- sub-69 is not one of the 192 genotyped participants — the question is closed.
- Scope C (eyes-closed rest + MSIT) is file-level identical to Scope B; the eyes-closed subset is carved out at epoch level in Phase 1.
- Derivative estimates assume a 250 Hz target rate, float32, with epoched + ICA overhead — see `reports/phase1_download_plan.md`.
- Confound tests run on the 79-subject analysis cohort (asserted from cohort_definition.csv).
- The full-EEG derivative estimate (~67 GB) far exceeds the 19 GB left after the raw download, which is why Scope A is rejected; Scope C fits with headroom and is therefore recommended (per the phase's budget logic, not an escalation).

## 7. Reproduction

```bash
python -m pearl_audit.cli run-all
```

All artifacts carry the same `run_id` (see `data/derivatives/phase0/_meta.json`); the report refuses to render mixed-run inputs.
