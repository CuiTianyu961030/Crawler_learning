'''
    More to see ~/Works/ScrapyProject and ~/Works/PortiaProject
'''


from scrapely import Scraper


def scrapely_test():
    s = Scraper()
    train_url = 'http://example.python-scraping.com/view/Afghanistan-1'
    s.train(train_url, {'name': 'Afghanistan', 'population': '29,121,286'})
    test_url = 'http://example.python-scraping.com/view/United-Kingdom-239'
    print(s.scrape(test_url))


if __name__ == '__main__':
    scrapely_test()
