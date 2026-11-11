"""Tests of the admin (web-app: Permissions; task-tracker: Tasks in the
admin)."""

from django.test import TestCase

from tasks.models import Task

from . import IndexMixin, demo_index, make_task, make_user, page

ADMIN = "/lab/admin/"
TASKS = "/lab/admin/tasks/task/"


class AdminCase(IndexMixin, TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.staff = make_user("boss", "BO", is_staff=True,
                              is_superuser=True)
        cls.worker = make_user("lab-worker-kl", "KL")
        cls.first = make_task(cls.worker, substance="Aspirin")
        cls.second = make_task(cls.worker, substance="Zimtsäure",
                               batch="B-77")
        cls.third = make_task(cls.worker, substance="Ferrocen")

    def setUp(self) -> None:
        self.use_index(demo_index())
        self.client.force_login(self.staff)


class AccessTests(AdminCase):

    def test_staff_enter(self) -> None:
        self.assertEqual(self.client.get(ADMIN).status_code, 200)

    def test_anonymous_users_are_sent_to_the_admin_sign_in(self) -> None:
        self.client.logout()
        for path in (ADMIN, TASKS):
            with self.subTest(path=path):
                done = self.client.get(path)
                self.assertEqual(done.status_code, 302)
                self.assertTrue(
                    done["Location"].startswith("/lab/admin/login/"))

    def test_users_without_staff_status_are_kept_out(self) -> None:
        self.client.force_login(self.worker)
        for path in (ADMIN, TASKS):
            with self.subTest(path=path):
                done = self.client.get(path)
                self.assertIn(done.status_code, (302, 403))
                if done.status_code == 302:
                    self.assertTrue(
                        done["Location"].startswith("/lab/admin/login/"))


class TaskListTests(AdminCase):

    def test_admin_list(self) -> None:
        """Scenario: Admin list."""
        done = self.client.get(TASKS)
        self.assertEqual(done.status_code, 200)
        text = done.content.decode("utf-8")
        positions = [text.find(t.number)
                     for t in (self.first, self.second, self.third)]
        self.assertNotIn(-1, positions)
        self.assertEqual(positions, sorted(positions))

    def test_search_by_number(self) -> None:
        text = self.client.get(f"{TASKS}?q={self.second.number}"
                               ).content.decode("utf-8")
        self.assertIn(self.second.number, text)
        self.assertNotIn(self.first.number, text)
        self.assertNotIn(self.third.number, text)

    def test_search_by_the_substance(self) -> None:
        """By its key and by its names."""
        fourth = make_task(self.worker, substance="CH-0012")
        for query in ("ferrocen", "cinnamic-acid", "cinnamic", "zimts"):
            wanted = self.third if query == "ferrocen" else fourth
            with self.subTest(query=query):
                text = self.client.get(
                    f"{TASKS}?q={query}").content.decode()
                self.assertIn(f"{TASKS}{wanted.pk}/change/", text)
                self.assertNotIn(f"{TASKS}{self.first.pk}/change/", text)

    def test_search_by_batch(self) -> None:
        text = self.client.get(f"{TASKS}?q=B-77").content.decode()
        self.assertIn(self.second.number, text)
        self.assertNotIn(self.first.number, text)
        self.assertNotIn(self.third.number, text)


class HistoryTests(AdminCase):

    def test_the_change_history_of_a_task(self) -> None:
        self.first._history_user = self.worker
        self.first.priority = "high"
        self.first.save()
        done = self.client.get(f"{TASKS}{self.first.pk}/history/")
        self.assertEqual(done.status_code, 200)
        self.assertIn("lab-worker-kl", done.content.decode("utf-8"))

    def test_deleting_a_task_does_not_free_its_number(self) -> None:
        done = self.client.post(f"{TASKS}{self.third.pk}/delete/",
                                {"post": "yes"})
        self.assertEqual(done.status_code, 302)
        self.assertFalse(Task.objects.filter(pk=self.third.pk).exists())
        fresh = make_task(self.worker)
        self.assertNotEqual(fresh.number, self.third.number)
        self.assertEqual(fresh.number, "T-004")


class AccountTests(AdminCase):

    def test_accounts_are_listed(self) -> None:
        done = self.client.get("/lab/admin/accounts/user/")
        self.assertEqual(done.status_code, 200)
        self.assertIn("lab-worker-kl", done.content.decode("utf-8"))

    def test_an_account_has_initials(self) -> None:
        done = self.client.get(
            f"/lab/admin/accounts/user/{self.worker.pk}/change/")
        self.assertEqual(done.status_code, 200)
        self.assertIsNotNone(page(done).find("input", name="initials"))

    def test_the_add_page_is_there(self) -> None:
        self.assertEqual(
            self.client.get("/lab/admin/accounts/user/add/").status_code,
            200)


class AccountDeletionTests(AdminCase):

    def test_accounts_cannot_be_deleted(self) -> None:
        """An account's name stays on the history it wrote."""
        from django.contrib.auth import get_user_model
        url = f"/lab/admin/accounts/user/{self.worker.pk}/delete/"
        self.assertEqual(self.client.post(url, {"post": "yes"}).status_code,
                         403)
        self.assertTrue(
            get_user_model().objects.filter(pk=self.worker.pk).exists())
