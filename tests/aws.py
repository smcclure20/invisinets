import aws
import logging
import unittest


TEST_DEPLOYMENT_ID: str = "fffff"


class AWSIntegrationTest(unittest.TestCase):

    deployment = aws.InvisinetAWS(TEST_DEPLOYMENT_ID)

    def test_resource_creation(self):
        eip = self.deployment.request_eip()
        self.assertEqual(len(self.deployment.active_eip()), 1)
        sip = self.deployment.request_sip()
        self.assertEqual(len(self.deployment.active_sip()), 1)

        eip.terminate()
        sip.terminate()

    def test_resource_deletion(self):
        n = 3
        eips = [self.deployment.request_eip(f"invisinet-test-eip-{i}") for i in range(n)]
        sips = [self.deployment.request_sip(f"invisinet-test-sip-{i}") for i in range(n)]

        self.assertEqual(len(self.deployment.active_eip()), n)
        self.assertEqual(len(self.deployment.active_sip()), n)

        for eip in eips:
            eip.terminate()
        for sip in sips:
            sip.terminate()

        self.assertEqual(len(self.deployment.active_eip()), 0)
        self.assertEqual(len(self.deployment.active_sip()), 0)



if __name__ == '__main__':
    logging.basicConfig(level="INFO")
    unittest.main()
