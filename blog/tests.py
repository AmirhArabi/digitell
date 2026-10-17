from django.test import Client, TestCase
from django.urls import reverse

from .models import BlogCategory, Post


class BlogPaginationTests(TestCase):
    """صفحه‌بندی وبلاگ (HTMX) با حفظ دستهٔ فعال و وضعیت‌های خالی/بارگذاری."""

    PAGE_SIZE = 6

    def setUp(self):
        self.client = Client()
        self.category = BlogCategory.objects.create(name="راهنمای خرید", slug="buying-guides")
        self.empty_category = BlogCategory.objects.create(name="اخبار", slug="news")
        for index in range(8):
            Post.objects.create(
                title=f"مقاله تست شماره {index + 1}",
                slug=f"test-post-{index + 1}",
                category=self.category,
                excerpt="چکیدهٔ تست",
                content="متن کامل مقالهٔ تست برای بررسی صفحه‌بندی.",
                is_published=True,
            )
        Post.objects.create(
            title="مقاله منتشرنشده",
            slug="draft-post",
            category=self.category,
            content="این مقاله نباید در فهرست دیده شود.",
            is_published=False,
        )

    def test_first_page_shows_only_published_page_size_posts(self):
        response = self.client.get(reverse('blog:post_list'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertEqual(content.count('مطالعه کامل'), self.PAGE_SIZE)
        self.assertContains(response, f'نمایش 1 تا {self.PAGE_SIZE} از 8 مقاله')
        self.assertNotContains(response, 'مقاله منتشرنشده')

    def test_second_page_shows_the_remaining_posts(self):
        response = self.client.get(reverse('blog:post_list'), {'page': 2})
        content = response.content.decode()
        self.assertEqual(content.count('مطالعه کامل'), 2)
        self.assertContains(response, 'نمایش 7 تا 8 از 8 مقاله')

    def test_out_of_range_page_falls_back_to_the_last_page(self):
        response = self.client.get(reverse('blog:post_list'), {'page': 99})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'نمایش 7 تا 8 از 8 مقاله')

    def test_category_page_keeps_its_path_in_page_links(self):
        response = self.client.get(
            reverse('blog:post_category', kwargs={'category_slug': self.category.slug})
        )
        content = response.content.decode()
        self.assertContains(response, 'دسته: راهنمای خرید')
        self.assertIn('?page=2', content)
        self.assertNotIn('href="/blog/?page=', content)

    def test_category_filter_moves_back_to_the_first_page(self):
        content = self.client.get(
            reverse('blog:post_category', kwargs={'category_slug': self.category.slug})
        ).content.decode()
        self.assertIn('?page=2', content)
        self.assertNotIn('?page=2&page=', content)

    def test_empty_category_shows_empty_state_without_pagination(self):
        response = self.client.get(
            reverse('blog:post_category', kwargs={'category_slug': self.empty_category.slug})
        )
        content = response.content.decode()
        self.assertContains(response, 'مقاله‌ای با این فیلتر یافت نشد')
        self.assertNotIn('aria-label="صفحه‌بندی مقالات"', content)

    def test_htmx_page_request_returns_the_grid_partial_only(self):
        response = self.client.get(reverse('blog:post_list'), {'page': 2}, HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn('<html', content)
        self.assertIn('id="post-list"', content)
        self.assertIn('نمایش 7 تا 8 از 8 مقاله', content)

    def test_loading_indicator_and_pagination_controls_are_present(self):
        content = self.client.get(reverse('blog:post_list')).content.decode()
        self.assertIn('id="posts-loading"', content)
        self.assertIn('hx-indicator="#posts-loading"', content)
        self.assertIn('در حال بارگذاری مقالات', content)
        self.assertIn('aria-label="صفحه‌بندی مقالات"', content)
