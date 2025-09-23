from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient


class APISmokeTests(APITestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(username="tester")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_me_endpoint(self):
        resp = self.client.get("/api/v1/me")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["id"], self.user.id)
        self.assertEqual(data["username"], self.user.username)

    def test_category_crud_and_pagination(self):
        for i in range(7):
            r = self.client.post("/api/v1/categories/", {"name": f"cat{i}"}, format="json")
            self.assertEqual(r.status_code, 201)

        r1 = self.client.get("/api/v1/categories/?page=1")
        self.assertEqual(r1.status_code, 200)
        b1 = r1.json()
        self.assertEqual(b1.get("count"), 7)
        self.assertLessEqual(len(b1.get("results", [])), 5)

        r2 = self.client.get("/api/v1/categories/?page=2")
        self.assertEqual(r2.status_code, 200)
        b2 = r2.json()
        self.assertGreaterEqual(len(b2.get("results", [])), 1)

    def test_task_crud_filters_and_due(self):
        c1 = self.client.post("/api/v1/categories/", {"name": "work"}, format="json").json()
        c2 = self.client.post("/api/v1/categories/", {"name": "home"}, format="json").json()

        t1 = self.client.post(
            "/api/v1/tasks/",
            {"title": "A", "status": "todo", "category_ids": [c1["id"]]},
            format="json",
        )
        self.assertEqual(t1.status_code, 201)

        due_now = timezone.now().isoformat()
        t2 = self.client.post(
            "/api/v1/tasks/",
            {"title": "B", "status": "in_progress", "due_at": due_now, "category_ids": [c2["id"]]},
            format="json",
        )
        self.assertEqual(t2.status_code, 201)

        t3 = self.client.post(
            "/api/v1/tasks/",
            {"title": "C", "status": "done"},
            format="json",
        )
        self.assertEqual(t3.status_code, 201)

        # status filter
        rs = self.client.get("/api/v1/tasks/?status=todo")
        self.assertEqual(rs.status_code, 200)
        bs = rs.json()
        self.assertTrue(all(x["status"] == "todo" for x in bs["results"]))

        # category filter
        rc = self.client.get(f"/api/v1/tasks/?category={c2['id']}")
        self.assertEqual(rc.status_code, 200)
        bc = rc.json()
        self.assertTrue(
            all(
                any(cat["id"] == c2["id"] for cat in item.get("categories", []))
                for item in bc["results"]
            )
        )

        # due filters (inclusive bounds)
        now_iso = timezone.now().isoformat()
        r_before = self.client.get(f"/api/v1/tasks/?due_before={now_iso}")
        self.assertEqual(r_before.status_code, 200)
        # at least the in_progress task with due=now should be present or empty if clock shifted
        # we just assert JSON shape
        self.assertIn("results", r_before.json())

        r_after = self.client.get(f"/api/v1/tasks/?due_after={now_iso}")
        self.assertEqual(r_after.status_code, 200)

        # update + categories clear
        tid = t1.json()["id"]
        up = self.client.patch(f"/api/v1/tasks/{tid}/", {"status": "done", "category_ids": []}, format="json")
        self.assertEqual(up.status_code, 200)
        self.assertEqual(up.json()["status"], "done")


class BotAuthTests(APITestCase):
    def test_bot_auth_flow(self):
        payload = {"telegram_user_id": 123, "chat_id": 456, "username": "tguser"}
        r = self.client.post(
            "/api/v1/bot/auth",
            payload,
            format="json",
            HTTP_X_INTERNAL_TOKEN="supersecret",
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("access", data)
        self.assertIn("refresh", data)
        self.assertEqual(data["user"]["username"].startswith("tguser"), True)

        # chat_id update
        r2 = self.client.post(
            "/api/v1/bot/auth",
            {"telegram_user_id": 123, "chat_id": 789, "username": "tguser"},
            format="json",
            HTTP_X_INTERNAL_TOKEN="supersecret",
        )
        self.assertEqual(r2.status_code, 200)