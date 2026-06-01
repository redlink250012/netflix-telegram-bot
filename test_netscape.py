from netflix_checker import parse_cookies

test = """.netflix.com	TRUE	/	TRUE	9999999999	NetflixId	v=3&ct=testvalue
.netflix.com	TRUE	/	TRUE	9999999999	SecureNetflixId	v=3&mac=testmac"""

result = parse_cookies(test)
print("Keys:", list(result.keys()))
print("NetflixId:", result.get("NetflixId", "MISSING"))
print("SecureNetflixId:", result.get("SecureNetflixId", "MISSING"))
