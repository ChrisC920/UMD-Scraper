import scrapy
from scrapy import signals
from datetime import datetime
from pytz import timezone
from UMD_Web_Scraper.settings import supabase_client

scraped_data = []

class CrawlingSpider(scrapy.Spider):

    def __init__(self, name=None, **kwargs):
        super().__init__(name, **kwargs)
        self.ending_time = None
        self.starting_time = datetime.now()
        # supabase_client.table('food_today_old').delete().neq("id", 0).execute()

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(CrawlingSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider, reason):

        ending_time = datetime.now()
        # supabase_client.table('food_today_old').insert(scraped_data).execute()

        # Insert into the food table while referencing the correct foreign keys
        for data in scraped_data:
            # Upsert the food item and get its ID
            food_response = supabase_client.table('foods').upsert({
                "name": data["name"],
                "link": data["link"],
                "serving_size": data["serving_size"],
                "servings_per_container": data["servings_per_container"].replace(" servings per container", ""),
                "calories_per_serving": data["calories_per_serving"].replace("\xa0", "").replace("Saturated Fat", ""),
                "total_fat": data["total_fat"],
                "saturated_fat": data["saturated_fat"],
                "trans_fat": data["trans_fat"],
                "total_carbohydrates": data["total_carbohydrates"],
                "dietary_fiber": data["dietary_fiber"].replace("\xa0", "").replace("Dietary Fiber", ""),
                "total_sugars": data["total_sugars"].replace("\xa0", "").replace("Total Sugars", ""),
                "added_sugars": data["added_sugars"].replace("\xa0", "")[9:].replace(" Added Sugars", ""),
                "cholesterol": data["cholesterol"],
                "sodium": data["sodium"],
                "protein": data["protein"]
            }, on_conflict="name, link").execute()

            food_id = food_response.data[0]['id']

            # Insert into dining_halls and get ID
            dining_hall_response = supabase_client.table('dining_halls').upsert({"name": data["dining_hall"]},
                                                                                on_conflict="name").execute()
            dining_hall_id = dining_hall_response.data[0]['id']

            # Associate food with dining hall
            supabase_client.table('food_dining_halls').upsert(
                {"food_id": food_id, "dining_hall_id": dining_hall_id}).execute()

            # Insert into meal_types and get ID
            meal_type_response = supabase_client.table('meal_types').upsert({"name": data["meal_type"]},
                                                                            on_conflict="name").execute()
            meal_type_id = meal_type_response.data[0]['id']

            # Associate food with meal type
            supabase_client.table('food_meal_types').upsert(
                {"food_id": food_id, "meal_type_id": meal_type_id}).execute()

            # Insert into sections and get ID
            section_response = supabase_client.table('sections').upsert({"name": data["section"]},
                                                                        on_conflict="name").execute()
            section_id = section_response.data[0]['id']

            supabase_client.table('dining_hall_sections').upsert(
                {"dining_hall_id": dining_hall_id, "section_id": section_id},
                on_conflict="dining_hall_id, section_id"
            ).execute()

            # Associate food with section
            supabase_client.table('food_sections').upsert({"food_id": food_id, "section_id": section_id}).execute()

            for allergen in data["allergens"]:
                # Insert allergen (ensuring uniqueness by name)
                allergen_response = supabase_client.table('allergens').upsert({"name": allergen},
                                                                              on_conflict="name").execute()
                allergen_id = allergen_response.data[0]['id']

                # Associate food with allergen
                supabase_client.table('food_allergens').upsert(
                    {"food_id": food_id, "allergen_id": allergen_id}).execute()

        print(f"Scraped {len(scraped_data)} items.")
        print("Time taken:", ending_time - self.starting_time)

    # tz = timezone('EST')
    # today_date = datetime.now(tz).strftime("%m/%d/%Y")
    today_date = "3/28/2025"
    name = "mycrawler"
    allow_domains = ["nutrition.umd.edu"]
    start_urls = [f"https://nutrition.umd.edu/?locationNum=19&dtdate={today_date}"
                  f"https://nutrition.umd.edu/?locationNum=51&dtdate={today_date}",
                  f"https://nutrition.umd.edu/?locationNum=16&dtdate={today_date}"]

    def parse(self, response, **kwargs):
        dining_hall = response.url[39:41]
        if dining_hall == "51":
            dining_hall = "251 North"
        elif dining_hall == "19":
            dining_hall = "Yahentamitsi"
        elif dining_hall == "16":
            dining_hall = "South"
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
        scraped_data.append(item)


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
