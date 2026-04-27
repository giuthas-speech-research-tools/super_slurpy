# Tracking Parameters

The following parameters control the behavior of the tracking
algorithms used in `slurpy`.

## Snake (Active Contour) Parameters

In computer vision, a "snake" is a flexible spline that
automatically deforms to map onto edges. It balances internal
forces (stiffness/elasticity) against external forces (image
features).

### `alpha: 0.1` (Continuity / Elasticity)

This parameter controls the **stretchiness** of the snake,
acting like a rubber band.
* **Function:** It penalizes the contour if anchor points get
  too far apart or cluster too closely. It maintains even
  spacing.
* **High values:** The snake acts like a tight rubber band.
  It resists stretching and may pull away from sharp corners
  to keep points close.
* **Low values:** The snake is loose. Points can stretch far
  to grab distant edges, but may bunch up in areas with high
  gradients.

### `lambda1: 0.5` (Smoothness / Energy Weighting)

This parameter controls the **stiffness** of the snake,
acting like a flexible wire.
* **Function:** It resists bending. In this implementation,
  `lambda1` balances the energy components to dictate overall
  curve smoothness.
* **High values:** The snake acts like a stiff wire. It
  resists sharp turns, resulting in smooth, sweeping curves
  that may ignore jagged details.
* **Low values:** The snake acts like a flexible string. It
  easily bends into sharp corners to perfectly hug every tiny
  variation in a boundary.

### `band_penalty: 10.0` (Boundary Constraint)

This is a spatial constraint used to prevent the contour from
wandering away from the target.
* **Function:** It acts as a penalty (a "wall") if points
  venture outside a defined target band around your initial
  anchor points.
* **High values:** Points trying to track edges outside the
  safe zone are heavily penalized, forcing the snake to stay
  near your initial guess.
* **Low values:** The snake is allowed to roam freely across
  the image to find the strongest edges, even if they are far
  from the starting position.

## Particle Filter Parameters

The particle filter uses statistical motion modeling to
generate and evaluate perturbed contours (particles) over
sequential frames.

### `num_particles: 50` (Particle Count)

This parameter defines the number of hypothesized contours.
* **Function:** It specifies how many unique particle
  variants to generate during evaluation.
* **High values:** More particles increase the chances of
  finding the optimal boundary but slow down processing time.
* **Low values:** Faster processing, but higher risk of losing
  the tracked object during rapid movement.

### `percent_var: 0.98` (Shape Model Variance)

This parameter handles the proportion of statistical variance
kept in the Principal Component Analysis (PCA).
* **Function:** Controls how much characteristic shape
  variation is permitted from the learned active shape model.
* **High values:** Retains more subtle shape deformations,
  allowing flexibility for complex bounds.
* **Low values:** Forces the tracker to adhere strictly to
  the most dominant mean shapes, rejecting unusual contour
  forms.

### `noise_scale: 1.0` (Tracking Spread)

This parameter controls the random noise multiplier.
* **Function:** Simulates potential state variations by
  applying Gaussian noise matched to the contour shape.
* **High values:** Particles spread out further, enabling
  recovery from sudden jumps or large frame-to-frame
  movements.
* **Low values:** Particles stay tightly clustered around the
  base contour, providing stable tracking for slow motions.

---

### Quick Tuning Guide

| Problem | Solution |
| :--- | :--- |
| Tracking is too jagged/noisy | Increase `lambda1` |
| Points cluster or leave gaps | Increase `alpha` |
| Snake snaps to wrong object | Increase `band_penalty` |
| Particle tracker loses object| Increase `noise_scale` |
| Tracker runs too slowly | Decrease `num_particles` |
