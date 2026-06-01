import httpx, json

netscape = """.netflix.com	TRUE	/	TRUE	9999999999	NetflixId	v=3&ct=BgjHlOvcAxKeAztP1NNF-kkvLs-5EVHkqpvOW81sk0EwR6qpTeIbGJaVK5BgqEGtYRREFxDm0nKdcG-hGK0Eu5cbPPoesw_Ql1vJUAAY7NayXeWfYS9SUlMvningHzXjrC2bRmRhQTmiziwpz-MoquGuxpH5YxscjYEhsOSi_uC7xZ7GSyK_yTQBYPY5gYdygHlaBrUD4SvxvCvb3DvsBBgzfgXdqjrNS8k_2gYs5FfGVOiIFAtkKLn5P6H1pQ37VgTDHDtr4fvJkYLEvJSbwhaKfov16o3efpUKetiEwf97TRnnDCFp2zyyMxNC6Mxgpa1ZTASlR06UnvQCWpb0d0RjsJWRK2kcMesf0eLcVAJj6ktEqM7uGle4UPI9O2nDihJ6kMdJ5VJJbqSj2xiLPs1wORTLOG7gPwsIawkBOuXKsdvUA3qDp-8lqaL-bt5nYATFwUTn6Ai8H-QZAPN2kLFc6Ufvgx8kbQallc0dInjA2qwxjESsQyPR9JEooUfs6mzj0CfPP41kAyq2coRx-a6bHrA0voOAjd5HMvEl0KZkPX514LXFZRgGIg4KDNIuIV9rmNgLbZPNqgQ..&pg=7VVC6VY2YFHJHDABOM6IYSCKLY&ch=AQEAEAABABQx2sTc5gnwsHyKul2rN11YGA6yLXJ0Yik.
.netflix.com	TRUE	/	TRUE	9999999999	SecureNetflixId	v=3&mac=AQEAEQABABR5462YOPu2CZmvmjgwDsonssrptoyxhf4.&dt=1766367640062"""

resp = httpx.post(
    "https://netflix-telegram-bot-production.up.railway.app/api/check",
    json={"cookies": netscape},
    timeout=30
)
data = resp.json()
print("Status:", resp.status_code)
print("Error:", data.get("error", "None"))
print("Valid:", data.get("valid"))
print("Token:", "SI" if data.get("token") else "NO")
if data.get("error"):
    print("Full:", json.dumps(data, indent=2))
