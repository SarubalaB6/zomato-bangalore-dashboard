-- Q1: Overall summary
SELECT COUNT(*) AS total_restaurants, ROUND(AVG(rate),2) AS avg_rating, ROUND(AVG(cost_for_two),0) AS avg_cost
FROM restaurants;

-- Q2: Top 10 areas by number of restaurants
SELECT location, COUNT(*) AS restaurants
FROM restaurants
GROUP BY location
ORDER BY restaurants DESC
LIMIT 10;

-- Q3: Top 10 best rated areas (min 50 restaurants)
SELECT location, ROUND(AVG(rate),2) AS avg_rating, COUNT(*) AS restaurants
FROM restaurants
GROUP BY location
HAVING COUNT(*) >= 50
ORDER BY avg_rating DESC
LIMIT 10;

-- Q4: Online order vs rating
SELECT online_order, COUNT(*) AS restaurants, ROUND(AVG(rate),2) AS avg_rating
FROM restaurants
GROUP BY online_order;

-- Q5: Top 10 highest rated restaurants (min 500 votes)
SELECT name, location, rate, votes
FROM restaurants
WHERE votes >= 500
ORDER BY rate DESC, votes DESC
LIMIT 10;

-- Q6: Restaurant types by count and average cost
SELECT rest_type, COUNT(*) AS restaurants, ROUND(AVG(cost_for_two),0) AS avg_cost
FROM restaurants
GROUP BY rest_type
ORDER BY restaurants DESC
LIMIT 10;

-- Q7: Table booking vs rating and cost
SELECT book_table, ROUND(AVG(rate),2) AS avg_rating, ROUND(AVG(cost_for_two),0) AS avg_cost
FROM restaurants
GROUP BY book_table;

-- Q8: Rating bands
SELECT CASE WHEN rate >= 4.0 THEN 'Excellent (4.0+)'
            WHEN rate >= 3.5 THEN 'Good (3.5-3.9)'
            ELSE 'Average (below 3.5)' END AS rating_band,
       COUNT(*) AS restaurants
FROM restaurants
GROUP BY rating_band
ORDER BY restaurants DESC;