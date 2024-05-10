import scrapy
from scrapy import signals
from datetime import datetime
from UMD_Web_Scraper.settings import supabase_client

scraped_data = []



class CrawlingSpider(scrapy.Spider):
    def __init__(self, name=None, **kwargs):
        super().__init__(name, **kwargs)
        self.ending_time = None
        self.starting_time = datetime.now()

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(CrawlingSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider, reason):
        ending_time = datetime.now()
        print("Time taken:", ending_time - self.starting_time)
        response = supabase_client.table('food').upsert(scraped_data, on_conflict=('name, dining_hall, section, meal_type, allergens', 'DO NOTHING'), ignore_duplicates=True).execute()
        print(f"Response: {response}")

    today_date = datetime.now().strftime("%m/%d/%Y")
    name = "mycrawler"
    allow_domains = ["nutrition.umd.edu"]
    start_urls = [f"https://nutrition.umd.edu/?locationNum=51&dtdate={today_date}",
                  f"https://nutrition.umd.edu/?locationNum=19&dtdate={today_date}",
                  f"https://nutrition.umd.edu/?locationNum=16&dtdate={today_date}"]

    custom_settings = {
        'FEEDS': {
            'output.json': {'format': 'json', 'overwrite': True},
        }
    }

    def parse(self, response, **kwargs):
        dining_hall = response.url[39:41]
        if dining_hall == "51":
            dining_hall = "251 North"
        elif dining_hall == "19":
            dining_hall = "Yahentamitsi"
        elif dining_hall == "16":
            dining_hall = "South Campus"
        else:
            dining_hall = "Unknown"

        num_meal_types = len(response.css(".tab-pane").getall())
        meal_type_list = []
        if num_meal_types == 3:
            breakfast_type = response.css("#pane-1")
            lunch_type = response.css("#pane-2")
            dinner_type = response.css("#pane-3")
            meal_type_list.append(breakfast_type)
            meal_type_list.append(lunch_type)
            meal_type_list.append(dinner_type)
        elif num_meal_types == 2:
            brunch_type = response.css("#pane-1")
            dinner_type = response.css("#pane-2")
            meal_type_list.append(brunch_type)
            meal_type_list.append(dinner_type)

        for meal_type in meal_type_list:
            section_list = meal_type.css(".card-body")
            for curr_section in section_list:
                section = curr_section.css("h5.card-title::text").get()
                rows = curr_section.css(".menu-item-row")
                for row in rows:
                    allergens = row.css(".nutri-icon::attr(title)").getall()
                    item = row.css(".menu-item-name")
                    link = "https://nutrition.umd.edu/" + item.css("::attr(href)").get()
                    yield response.follow(link, callback=self.parse_item,
                                          cb_kwargs={"section": section, "dining_hall": dining_hall, "meal_type": meal_type, "num_meal_types": num_meal_types, "allergens": allergens})

    @staticmethod
    def parse_item(response, section, dining_hall, meal_type, num_meal_types, allergens):
        item = {
            "name": response.css("h2::text").get().title(),
            "dining_hall": dining_hall,
            "meal_type": convert_meal_type(meal_type, num_meal_types),
            "section": section,
            "link": response.url,
            "serving_size": response.css(".nutfactsservsize::text")[1].get().lower(),
            "servings_per_container": response.css(".nutfactsservpercont::text").get().lower(),
            "calories_per_serving": response.css("td p::text")[1].get(),
            "total_fat": response.css(".nutfactstopnutrient::text")[0].get(),
            "saturated_fat": response.css(".nutfactstopnutrient::text")[2].get(),
            "trans_fat": response.css(".nutfactstopnutrient *::text")[4].get(),
            "total_carbohydrates": response.css(".nutfactstopnutrient::text")[1].get(),
            "dietary_fiber": response.css(".nutfactstopnutrient::text")[3].get(),
            "total_sugars": response.css(".nutfactstopnutrient::text")[6].get(),
            "added_sugars": response.css(".nutfactstopnutrient::text")[8].get(),
            "cholesterol": response.css(".nutfactstopnutrient::text")[7].get(),
            "sodium": response.css(".nutfactstopnutrient::text")[9].get(),
            "protein": response.css(".nutfactstopnutrient::text")[10].get(),
            "allergens": allergens
        }
        yield item


def convert_meal_type(meal_type_selector, num_meal_types):
    meal_type_id = meal_type_selector.attrib["id"]
    if num_meal_types == 3:
        if meal_type_id == 'pane-1':
            return 'Breakfast'
        elif meal_type_id == 'pane-2':
            return 'Lunch'
        elif meal_type_id == 'pane-3':
            return 'Dinner'
    else:
        if meal_type_id == 'pane-1':
            return 'Brunch'
        elif meal_type_id == 'pane-2':
            return 'Dinner'
    raise Exception('Unknown meal')