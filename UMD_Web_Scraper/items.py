# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class WebscraperItem(scrapy.Item):
    name = scrapy.Field()
    pass


class FoodItem(scrapy.Item):
    name = scrapy.Field()
    dining_hall = scrapy.Field()
    section = scrapy.Field()
    link = scrapy.Field()
    meal_type = scrapy.Field()
    serving_size = scrapy.Field()
    servings_per_container = scrapy.Field()
    calories_per_serving = scrapy.Field()
    total_fat = scrapy.Field()
    saturated_fat = scrapy.Field()
    trans_fat = scrapy.Field()
    total_carbohydrates = scrapy.Field()
    dietary_fiber = scrapy.Field()
    total_sugars = scrapy.Field()
    added_sugars = scrapy.Field()
    cholesterol = scrapy.Field()
    sodium = scrapy.Field()
    protein = scrapy.Field()
    allergens = scrapy.Field()
