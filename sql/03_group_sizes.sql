-- How many people are in treatment vs. control?
-- The design split is 85% treatment / 15% control.
SELECT
    CASE WHEN treatment = 1 THEN 'treatment' ELSE 'control' END AS grp,
    COUNT(*)                                AS n_users,
    COUNT(*) / SUM(COUNT(*)) OVER ()        AS share_of_users
FROM criteo
GROUP BY treatment
ORDER BY treatment;
