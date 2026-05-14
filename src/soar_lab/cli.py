import argparse
import os


def main() -> int:
    parser = argparse.ArgumentParser(prog="soar-lab", description="SOAR Ransomware Lab command line interface")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("version", help="Show package version")

    api_parser = subparsers.add_parser("api", help="Run the management API")
    api_parser.add_argument("--host", default=os.getenv("API_HOST", "127.0.0.1"))
    api_parser.add_argument("--port", type=int, default=int(os.getenv("API_PORT", "8000")))

    send_alert_parser = subparsers.add_parser("send-alert", help="Run the SIEM alert simulator")
    send_alert_parser.add_argument("--webhook-url", default=os.getenv("SHUFFLE_WEBHOOK_URL", "http://localhost:5001/webhook"))
    send_alert_parser.add_argument("--api-token", default=os.getenv("SIEM_WEBHOOK_TOKEN", "siem-webhook-token-change-this"))
    send_alert_parser.add_argument("--num-alerts", type=int, default=3)
    send_alert_parser.add_argument("--delay", type=int, default=5)
    send_alert_parser.add_argument("--type", choices=["malicious", "benign"], default="malicious")
    send_alert_parser.add_argument("--single", action="store_true")

    args = parser.parse_args()

    if args.command == "version":
        from soar_lab import __version__
        print(__version__)
        return 0

    if args.command == "api":
        import uvicorn
        uvicorn.run("soar_lab.api.main:app", host=args.host, port=args.port)
        return 0

    if args.command == "send-alert":
        from soar_lab.services.send_alert import SIEMSimulator
        simulator = SIEMSimulator(args.webhook_url, args.api_token)
        if args.single:
            alert = simulator.generate_alert(args.type)
            if simulator.validate_alert(alert):
                return 0 if simulator.send_alert(alert) else 1
            return 1
        return 0 if simulator.run_simulation(args.num_alerts, args.delay, args.type) else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
