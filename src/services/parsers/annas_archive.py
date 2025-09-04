from .base import BookParser


class AABookParser(BookParser):
    """Parser for Anna's Archive book pages."""
    
    def _parse_search_result_row(row: Tag) -> Optional[BookInfo]:
        """Parse a single search result row into a BookInfo object."""
        try:
            cells = row.find_all("td")
            preview_img = cells[0].find("img")
            preview = preview_img["src"] if preview_img else None

            return BookInfo(
                id=row.find_all("a")[0]["href"].split("/")[-1],
                preview=preview,
                title=cells[1].find("span").next,
                author=cells[2].find("span").next,
                publisher=cells[3].find("span").next,
                year=cells[4].find("span").next,
                language=cells[7].find("span").next,
                format=cells[9].find("span").next.lower(),
                size=cells[10].find("span").next,
            )
        except Exception as e:
            logger.error_trace(f"Error parsing search result row: {e}")
            return None



    def _parse_book_info_page(self, soup: BeautifulSoup, book_id: str) -> BookInfo:
        """Parse the book info page HTML into a BookInfo object."""
        data = soup.select_one("body > main > div:nth-of-type(1)")

        if not data:
            raise Exception(f"Failed to parse book info for ID: {book_id}")

        preview: str = ""

        node = data.select_one("div:nth-of-type(1) > img")
        if node:
            preview_value = node.get("src", "")
            if isinstance(preview_value, list):
                preview = preview_value[0]
            else:
                preview = preview_value

        data = soup.find_all("div", {"class": "main-inner"})[0].find_next("div")
        divs = list(data.children)
        format = divs[13].text.split(" · ")[-6].strip().lower()
        size = divs[13].text.split(" · ")[-5].strip().lower()

        every_url = soup.find_all("a")
        slow_urls_no_waitlist = set()
        slow_urls_with_waitlist = set()
        external_urls_libgen = set()
        external_urls_z_lib = set()
        external_urls_welib = set()

        for url in every_url:
            try:
                if url.text.strip().lower().startswith("slow partner server"):
                    if (
                        url.next is not None
                        and url.next.next is not None
                        and "waitlist" in url.next.next.strip().lower()
                    ):
                        internal_text = url.next.next.strip().lower()
                        if "no waitlist" in internal_text:
                            slow_urls_no_waitlist.add(url["href"])
                        else:
                            slow_urls_with_waitlist.add(url["href"])
                elif (
                    url.next is not None
                    and url.next.next is not None
                    and "click “GET” at the top" in url.next.next.text.strip()
                ):
                    libgen_url = url["href"]
                    # TODO : Temporary fix ? Maybe get URLs from https://open-slum.org/ ?
                    libgen_url = re.sub(r'libgen\.(lc|is|bz|st)', 'libgen.gl', url["href"])

                    external_urls_libgen.add(libgen_url)
                elif url.text.strip().lower().startswith("z-lib"):
                    if ".onion/" not in url["href"]:
                        external_urls_z_lib.add(url["href"])
            except:
                pass

        external_urls_welib = _get_download_urls_from_welib(book_id) if USE_CF_BYPASS else set()

        urls = []
        urls += list(external_urls_welib) if PRIORITIZE_WELIB else []
        urls += list(slow_urls_no_waitlist) if USE_CF_BYPASS else []
        urls += list(external_urls_libgen)
        urls += list(external_urls_welib) if not PRIORITIZE_WELIB else []
        urls += list(slow_urls_with_waitlist)  if USE_CF_BYPASS else []
        urls += list(external_urls_z_lib)

        for i in range(len(urls)):
            urls[i] = downloader.get_absolute_url(AA_BASE_URL, urls[i])

        # Remove empty urls
        urls = [url for url in urls if url != ""]

        # Extract basic information
        book_info = BookInfo(
            id=book_id,
            preview=preview,
            title=divs[7].next.strip(),
            publisher=divs[11].text.strip(),
            author=divs[9].text.strip(),
            format=format,
            size=size,
            download_urls=urls,
        )

        # Extract additional metadata
        info = _extract_book_metadata(divs[-6])
        book_info.info = info

        # Set language and year from metadata if available
        if info.get("Language"):
            book_info.language = info["Language"][0]
        if info.get("Year"):
            book_info.year = info["Year"][0]

        return book_info