# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from UMD_Web_Scraper.spiders.crawling_spider import scraped_data


def remove_non_alphanumeric(input_string):
    alphanumeric_string = ""

    for char in input_string:
        if char.isalnum():
            alphanumeric_string += char

    return alphanumeric_string


class UmdWebScraperPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        field_names = adapter.field_names()

        for field_name in field_names:
            if field_name != "dining_hall" and field_name != "meal_type" and field_name != "allergens" and field_name != "link":
                value = adapter.get(field_name)
                adapter[field_name] = value.replace('\xa0', '')

        value = adapter.get('section')
        adapter['section'] = value.strip()
        value = adapter.get('saturated_fat')
        adapter['saturated_fat'] = value.replace("Saturated Fat", '')
        value = adapter.get('dietary_fiber')
        adapter['dietary_fiber'] = value.replace("Dietary Fiber", '')
        value = adapter.get('total_sugars')
        adapter['total_sugars'] = value.replace("Total Sugars", '')
        value = adapter.get('added_sugars')
        adapter['added_sugars'] = value[9:].replace(" Added Sugars", '')
        scraped_data.append(item)
        return item
