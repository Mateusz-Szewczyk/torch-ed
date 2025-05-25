#!/usr/bin/env python3
"""
Kompletny skrypt testujący wszystkie endpointy user_auth i user_info
Nie testuje funkcji wysyłania e-mail
"""

import requests
import time
import json
from datetime import datetime

# Konfiguracja
API_BASE_URLS = [
    "http://localhost:14440/api/v1",  # Główny port
    "http://localhost:8043/api/v1",  # Alternatywny port
    "http://localhost:5000/api/v1",  # Flask dev port
    "http://localhost:3001/api/v1",  # Backup port
]


# Kolory dla outputu
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")


def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")


def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️ {msg}{Colors.END}")


def print_info(msg):
    print(f"{Colors.BLUE}ℹ️ {msg}{Colors.END}")


def print_header(msg):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}\n")


class APITester:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = None
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }

        # Dane testowe
        self.test_users = [
            {
                "user_name": "testuser1@example.com",
                "password": "TestPassword1!",
                "password2": "TestPassword1!",
                "email": "testuser1@example.com",
                "age": 25,
                "role": "user"
            },
            {
                "user_name": "testuser2@example.com",
                "password": "SecurePass2@",
                "password2": "SecurePass2@",
                "email": "testuser2@example.com",
                "age": 30,
                "role": "user"
            }
        ]

    def find_working_server(self):
        """Znajdź działający serwer"""
        print_info("Szukanie działającego serwera...")

        for url in API_BASE_URLS:
            try:
                response = self.session.get(f"{url}/auth/session-check", timeout=3)
                print_success(f"Znaleziono działający serwer: {url}")
                self.base_url = url
                return True
            except requests.exceptions.RequestException:
                print_warning(f"Serwer niedostępny: {url}")
                continue

        print_error("Nie znaleziono działającego serwera!")
        print_info("Uruchom serwer na jednym z portów: 14440, 8043, 5000, 3001")
        return False

    def record_test(self, name, success, message="", response=None):
        """Zapisz wynik testu"""
        if success:
            self.test_results['passed'] += 1
            print_success(f"{name}: {message}")
        else:
            self.test_results['failed'] += 1
            print_error(f"{name}: {message}")

        self.test_results['details'].append({
            'name': name,
            'success': success,
            'message': message,
            'response_code': response.status_code if response else None,
            'timestamp': datetime.now().isoformat()
        })

    def test_register(self, user_data):
        """Test rejestracji użytkownika"""
        try:
            response = self.session.post(f"{self.base_url}/auth/register", json=user_data)

            if response.status_code == 201:
                data = response.json()
                if data.get('success'):
                    self.record_test("Registration", True, f"User {user_data['email']} registered", response)
                    return True
                else:
                    self.record_test("Registration", False, f"Registration failed: {data.get('error')}", response)
            elif response.status_code == 400:
                data = response.json()
                if "already exists" in data.get('error', ''):
                    self.record_test("Registration", True, f"User {user_data['email']} already exists", response)
                    return True
                else:
                    self.record_test("Registration", False, f"Registration error: {data.get('error')}", response)
            else:
                self.record_test("Registration", False, f"Unexpected status: {response.status_code}", response)

        except Exception as e:
            self.record_test("Registration", False, f"Exception: {str(e)}")

        return False

    def test_login(self, user_data):
        """Test logowania"""
        try:
            login_data = {
                "user_name": user_data["email"],
                "password": user_data["password"]
            }

            response = self.session.post(f"{self.base_url}/auth/login", json=login_data)

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.record_test("Login", True, f"User {user_data['email']} logged in", response)
                    return True
                else:
                    self.record_test("Login", False, f"Login failed: {data.get('error')}", response)
            elif response.status_code == 423:
                data = response.json()
                self.record_test("Login", True, f"Account not confirmed (expected): {data.get('error')}", response)
                return True  # This is expected behavior for unconfirmed accounts
            else:
                data = response.json()
                self.record_test("Login", False, f"Login failed: {data.get('error')}", response)

        except Exception as e:
            self.record_test("Login", False, f"Exception: {str(e)}")

        return False

    def test_session_check(self):
        """Test sprawdzenia sesji"""
        try:
            response = self.session.get(f"{self.base_url}/auth/session-check")

            if response.status_code == 200:
                data = response.json()
                if data.get('authenticated'):
                    self.record_test("Session Check", True, f"Authenticated as {data.get('email')}", response)
                    return data
                else:
                    self.record_test("Session Check", False, "Not authenticated", response)
            elif response.status_code == 401:
                self.record_test("Session Check", True, "Not logged in (expected)", response)
                return None
            else:
                self.record_test("Session Check", False, f"Unexpected status: {response.status_code}", response)

        except Exception as e:
            self.record_test("Session Check", False, f"Exception: {str(e)}")

        return None

    def test_profile_get(self):
        """Test pobrania profilu"""
        try:
            response = self.session.get(f"{self.base_url}/user/profile")

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    user_info = data.get('user', {})
                    self.record_test("Profile GET", True, f"Profile retrieved for {user_info.get('email')}", response)
                    return user_info
                else:
                    self.record_test("Profile GET", False, "Failed to get profile", response)
            elif response.status_code == 401:
                self.record_test("Profile GET", True, "Unauthorized (expected when not logged in)", response)
            else:
                data = response.json()
                self.record_test("Profile GET", False, f"Error: {data.get('error')}", response)

        except Exception as e:
            self.record_test("Profile GET", False, f"Exception: {str(e)}")

        return None

    def test_profile_update(self, new_username):
        """Test aktualizacji profilu"""
        try:
            response = self.session.put(f"{self.base_url}/user/profile", json={"username": new_username})

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.record_test("Profile Update", True, f"Username updated to {new_username}", response)
                    return True
                else:
                    self.record_test("Profile Update", False, f"Update failed: {data.get('error')}", response)
            else:
                data = response.json()
                self.record_test("Profile Update", False, f"Error: {data.get('error')}", response)

        except Exception as e:
            self.record_test("Profile Update", False, f"Exception: {str(e)}")

        return False

    def test_change_password(self, current_password, new_password):
        """Test zmiany hasła"""
        try:
            change_data = {
                "currentPassword": current_password,
                "newPassword": new_password
            }

            response = self.session.post(f"{self.base_url}/user/change-password", json=change_data)

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.record_test("Change Password", True, "Password changed successfully", response)
                    return True
                else:
                    self.record_test("Change Password", False, f"Change failed: {data.get('error')}", response)
            else:
                data = response.json()
                self.record_test("Change Password", False, f"Error: {data.get('error')}", response)

        except Exception as e:
            self.record_test("Change Password", False, f"Exception: {str(e)}")

        return False

    def test_export_data(self):
        """Test eksportu danych"""
        try:
            response = self.session.get(f"{self.base_url}/user/export-data")

            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    self.record_test("Export Data", True, f"Data exported successfully ({len(response.content)} bytes)",
                                     response)
                    return True
                else:
                    self.record_test("Export Data", False, f"Unexpected content type: {content_type}", response)
            else:
                try:
                    data = response.json()
                    self.record_test("Export Data", False, f"Error: {data.get('error')}", response)
                except:
                    self.record_test("Export Data", False, f"Status: {response.status_code}", response)

        except Exception as e:
            self.record_test("Export Data", False, f"Exception: {str(e)}")

        return False

    def test_logout(self):
        """Test wylogowania"""
        try:
            response = self.session.get(f"{self.base_url}/auth/logout")

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.record_test("Logout", True, "Logged out successfully", response)
                    return True
                else:
                    self.record_test("Logout", False, f"Logout failed: {data.get('error')}", response)
            else:
                try:
                    data = response.json()
                    self.record_test("Logout", False, f"Error: {data.get('error')}", response)
                except:
                    self.record_test("Logout", False, f"Status: {response.status_code}", response)

        except Exception as e:
            self.record_test("Logout", False, f"Exception: {str(e)}")

        return False

    def test_password_requirements(self):
        """Test wymagań hasła"""
        weak_passwords = [
            "123456",  # Too short
            "password",  # No uppercase, number, special
            "PASSWORD",  # No lowercase, number, special
            "Password",  # No number, special
            "Password1",  # No special character
        ]

        user_data = self.test_users[0].copy()

        for weak_password in weak_passwords:
            user_data["password"] = weak_password
            user_data["password2"] = weak_password
            user_data["email"] = f"weak_{weak_password}@example.com"

            try:
                response = self.session.post(f"{self.base_url}/auth/register", json=user_data)
                if response.status_code == 400:
                    self.record_test("Password Validation", True, f"Correctly rejected weak password: {weak_password}",
                                     response)
                else:
                    self.record_test("Password Validation", False, f"Should reject weak password: {weak_password}",
                                     response)
            except Exception as e:
                self.record_test("Password Validation", False, f"Exception testing {weak_password}: {str(e)}")

    def test_authentication_required_endpoints(self):
        """Test endpointów wymagających autoryzacji"""
        # Wyloguj się najpierw
        self.test_logout()

        protected_endpoints = [
            ("GET", "/user/profile", "Profile GET"),
            ("PUT", "/user/profile", "Profile PUT"),
            ("POST", "/user/change-password", "Change Password"),
            ("GET", "/user/export-data", "Export Data"),
            ("DELETE", "/user/delete-account", "Delete Account"),
        ]

        for method, endpoint, name in protected_endpoints:
            try:
                if method == "GET":
                    response = self.session.get(f"{self.base_url}{endpoint}")
                elif method == "PUT":
                    response = self.session.put(f"{self.base_url}{endpoint}", json={"username": "test"})
                elif method == "POST":
                    response = self.session.post(f"{self.base_url}{endpoint}", json={"test": "data"})
                elif method == "DELETE":
                    response = self.session.delete(f"{self.base_url}{endpoint}", json={"confirmation": "USUŃ KONTO"})

                if response.status_code == 401:
                    self.record_test(f"Auth Required - {name}", True, "Correctly requires authentication", response)
                else:
                    self.record_test(f"Auth Required - {name}", False,
                                     f"Should require auth, got {response.status_code}", response)

            except Exception as e:
                self.record_test(f"Auth Required - {name}", False, f"Exception: {str(e)}")

    def run_comprehensive_tests(self):
        """Uruchom wszystkie testy"""
        print_header("COMPREHENSIVE API TESTING SUITE")

        if not self.find_working_server():
            return

        # Test 1: Password Requirements
        print_header("TEST 1: PASSWORD VALIDATION")
        self.test_password_requirements()

        # Test 2: Registration and Login Flow
        print_header("TEST 2: REGISTRATION & LOGIN FLOW")
        user = self.test_users[0]

        if self.test_register(user):
            # Note: In real scenario, email confirmation would be needed
            # For testing, we assume account is confirmed or we handle 423 status
            login_success = self.test_login(user)

            if login_success:
                # Test 3: Authenticated Operations
                print_header("TEST 3: AUTHENTICATED OPERATIONS")

                session_data = self.test_session_check()
                profile_data = self.test_profile_get()

                if profile_data:
                    # Test profile update
                    new_username = f"updated_user_{int(time.time())}"
                    self.test_profile_update(new_username)

                    # Test password change
                    new_password = "NewPassword123!"
                    if self.test_change_password(user["password"], new_password):
                        # Update user data for future tests
                        user["password"] = new_password

                    # Test data export
                    self.test_export_data()

        # Test 4: Authentication Requirements
        print_header("TEST 4: AUTHENTICATION REQUIREMENTS")
        self.test_authentication_required_endpoints()

        # Test 5: Edge Cases
        print_header("TEST 5: EDGE CASES")
        self.test_edge_cases()

        # Final Results
        self.print_final_results()

    def test_edge_cases(self):
        """Test przypadków brzegowych"""
        # Test malformed JSON
        try:
            response = self.session.post(f"{self.base_url}/auth/register", data="invalid json")
            if response.status_code in [400, 422]:
                self.record_test("Edge Case - Invalid JSON", True, "Correctly handles malformed JSON", response)
            else:
                self.record_test("Edge Case - Invalid JSON", False, f"Unexpected status: {response.status_code}",
                                 response)
        except Exception as e:
            self.record_test("Edge Case - Invalid JSON", False, f"Exception: {str(e)}")

        # Test missing fields
        try:
            response = self.session.post(f"{self.base_url}/auth/register", json={"email": "test@test.com"})
            if response.status_code == 400:
                self.record_test("Edge Case - Missing Fields", True, "Correctly validates required fields", response)
            else:
                self.record_test("Edge Case - Missing Fields", False, f"Should validate required fields", response)
        except Exception as e:
            self.record_test("Edge Case - Missing Fields", False, f"Exception: {str(e)}")

        # Test invalid email format
        invalid_user = self.test_users[0].copy()
        invalid_user["email"] = "invalid-email"
        invalid_user["user_name"] = "invalid-email"

        try:
            response = self.session.post(f"{self.base_url}/auth/register", json=invalid_user)
            if response.status_code == 400:
                self.record_test("Edge Case - Invalid Email", True, "Correctly validates email format", response)
            else:
                self.record_test("Edge Case - Invalid Email", False, f"Should validate email format", response)
        except Exception as e:
            self.record_test("Edge Case - Invalid Email", False, f"Exception: {str(e)}")

    def print_final_results(self):
        """Wydrukuj podsumowanie wyników"""
        print_header("FINAL TEST RESULTS")

        total_tests = self.test_results['passed'] + self.test_results['failed']
        pass_rate = (self.test_results['passed'] / total_tests * 100) if total_tests > 0 else 0

        print(f"Total Tests: {total_tests}")
        print_success(f"Passed: {self.test_results['passed']}")
        print_error(f"Failed: {self.test_results['failed']}")
        print(f"Pass Rate: {pass_rate:.1f}%")

        if pass_rate >= 90:
            print_success("🎉 EXCELLENT! API is working very well!")
        elif pass_rate >= 70:
            print_warning("✨ GOOD! API is mostly working, some issues to address")
        else:
            print_error("🔧 NEEDS WORK! Several issues need to be fixed")

        # Detailed results
        print_header("DETAILED RESULTS")
        for result in self.test_results['details']:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"{status} | {result['name']} | {result['message']}")

        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"api_test_results_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(self.test_results, f, indent=2)

        print_info(f"Detailed results saved to: {filename}")


def main():
    """Główna funkcja"""
    print_info("Starting comprehensive API tests...")
    print_info("Make sure your server is running on one of the supported ports")

    tester = APITester()
    tester.run_comprehensive_tests()


if __name__ == "__main__":
    main()
