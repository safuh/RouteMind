# Multimodal Transportation Graph

RouteMind represents logistics infrastructure as a **time-dependent directed graph**.

A node is a physical logistics location. An edge is a scheduled transportation service rather than simply a road distance.

```text
Nairobi
  │
  ├── Truck 08:00 → Nakuru 15:00
  │
  └── Bus   09:00 → Nakuru 12:00
                    │
                    ├── Truck → Kisumu
                    └── Bus   → Kisumu
```

Each edge retains:

- provider;
- transport mode;
- departure and arrival;
- weight capacity;
- volume capacity;
- price;
- currency;
- reliability;
- restrictions.

This prevents the optimization layer from losing operational information that an ordinary shortest-path graph would discard.

## Why time-dependent?

A shipment ready at 08:15 cannot board a service that departed at 08:00. Likewise, a cheap connection may be inferior to a more expensive service when the waiting time causes a deadline violation.

The graph is therefore intended to support state such as:

```text
current_location
current_time
remaining_weight_capacity
remaining_volume_capacity
transfers
cost
reliability
```

The next layer will use these semantics to discover feasible direct and multimodal candidate paths.
