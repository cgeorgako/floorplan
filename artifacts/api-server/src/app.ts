import express, { type Express, type Request, type Response } from "express";
import cors from "cors";
import pinoHttp from "pino-http";
import http from "node:http";
import router from "./routes";
import { logger } from "./lib/logger";

const app: Express = express();

app.use(
  pinoHttp({
    logger,
    serializers: {
      req(req) {
        return {
          id: req.id,
          method: req.method,
          url: req.url?.split("?")[0],
        };
      },
      res(res) {
        return {
          statusCode: res.statusCode,
        };
      },
    },
  }),
);
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use("/api", router);

// Forward everything else to the Flask app running on port 5000.
app.use((req: Request, res: Response) => {
  const options: http.RequestOptions = {
    hostname: "127.0.0.1",
    port: 5000,
    path: req.url,
    method: req.method,
    headers: { ...req.headers, host: "127.0.0.1:5000" },
  };

  const proxy = http.request(options, (flaskRes) => {
    res.status(flaskRes.statusCode ?? 502);
    Object.entries(flaskRes.headers).forEach(([k, v]) => {
      if (v !== undefined) res.setHeader(k, v);
    });
    flaskRes.pipe(res, { end: true });
  });

  proxy.on("error", (err) => {
    logger.error({ err }, "Flask proxy error");
    if (!res.headersSent) res.status(502).send("Flask app unavailable");
  });

  req.pipe(proxy, { end: true });
});

export default app;
