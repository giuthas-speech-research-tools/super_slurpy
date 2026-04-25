# Snake Algorithm Parameters

The following parameters control the behavior of the **"Snake" (Active 
Contour)** algorithm used in `slurpy`. In computer vision, a "snake" is 
a flexible spline that automatically deforms to map onto edges. It balances 
internal forces (stiffness/elasticity) against external forces (image 
features).

## `alpha: 0.1` (Continuity / Elasticity)

This parameter controls the **stretchiness** of the snake, acting like a 
rubber band.
* **Function:** It penalizes the contour if anchor points get too far apart 
  or cluster too closely. It maintains even spacing.
* **High values:** The snake acts like a tight rubber band. It resists 
  stretching and may pull away from sharp corners to keep points close.
* **Low values:** The snake is loose. Points can stretch far to grab 
  distant edges, but may bunch up in areas with high gradients.

## `lambda1: 0.5` (Smoothness / Energy Weighting)

This parameter controls the **stiffness** of the snake, acting like a 
flexible wire.
* **Function:** It resists bending. In this implementation, `lambda1` 
  balances the energy components to dictate overall curve smoothness.
* **High values:** The snake acts like a stiff wire. It resists sharp 
  turns, resulting in smooth, sweeping curves that may ignore jagged 
  details.
* **Low values:** The snake acts like a flexible string. It easily bends 
  into sharp corners to perfectly hug every tiny variation in a boundary.

## `band_penalty: 10.0` (Boundary Constraint)

This is a spatial constraint used to prevent the contour from wandering 
away from the target.
* **Function:** It acts as a penalty (a "wall") if points venture outside 
   a defined target band around your initial anchor points.
* **High values:** Points trying to track edges outside the safe zone are 
  heavily penalized, forcing the snake to stay near your initial guess.
* **Low values:** The snake is allowed to roam freely across the image to 
  find the strongest edges, even if they are far from the starting 
  position.

---

### Quick Tuning Guide

| Problem | Solution |
| :--- | :--- |
| Tracking is too jagged/noisy | Increase `lambda1` |
| Points are clustering or leaving gaps | Increase `alpha` |
| Snake snaps to the wrong object entirely | Increase `band_penalty` |