# Minimal recursive Unbound resolver for the adguardctl integration test stack.
# Built from Alpine (native multi-arch, incl. arm64) rather than a prebuilt image
# so it mirrors this repo's install.sh Unbound config exactly and ships a shell +
# drill for a real healthcheck.
FROM alpine:3.20

RUN apk add --no-cache unbound drill ca-certificates \
    && mkdir -p /etc/unbound

# Root hints + DNSSEC trust anchor (fetched at build time; build has network).
# unbound-anchor exits non-zero when it first creates the key — that is expected.
RUN wget -qO /etc/unbound/root.hints https://www.internic.net/domain/named.root \
    && (unbound-anchor -a /etc/unbound/root.key || true)

COPY unbound.conf /etc/unbound/unbound.conf
RUN unbound-checkconf /etc/unbound/unbound.conf

EXPOSE 5335/udp 5335/tcp

ENTRYPOINT ["unbound", "-d", "-c", "/etc/unbound/unbound.conf"]
