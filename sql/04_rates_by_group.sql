-- What share of each group visited, converted, and saw the ad?
-- Also: conversion among visitors, and visit/conversion split by exposure inside treatment.
SELECT
    CASE WHEN treatment = 1 THEN 'treatment' ELSE 'control' END AS grp,
    COUNT(*)                                        AS n_users,
    AVG(visit)                                      AS visit_rate,
    AVG(conversion)                                 AS conversion_rate,
    AVG(exposure)                                   AS exposure_rate,
    SUM(conversion) / NULLIF(SUM(visit), 0)         AS conversion_per_visit
FROM criteo
GROUP BY treatment

UNION ALL

-- Inside treatment only: people who saw the ad vs. people who did not.
-- WARNING: this is NOT a fair comparison (exposure was not randomized). Shown only to flag it.
SELECT
    CASE WHEN exposure = 1 THEN 'treatment, exposed' ELSE 'treatment, not exposed' END,
    COUNT(*),
    AVG(visit),
    AVG(conversion),
    AVG(exposure),
    SUM(conversion) / NULLIF(SUM(visit), 0)
FROM criteo
WHERE treatment = 1
GROUP BY exposure
ORDER BY grp;
