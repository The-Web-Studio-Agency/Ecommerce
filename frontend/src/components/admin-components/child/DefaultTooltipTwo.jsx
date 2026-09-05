"use client";
import React, { useEffect } from "react";

const DefaultTooltipTwo = () => {
  useEffect(() => {
    // Ensure the code runs only in the browser
    if (typeof window !== "undefined") {
      // Dynamically import Tooltip to avoid SSR issues
      import("bootstrap/dist/js/bootstrap.bundle.min.js").then(
        ({ Tooltip }) => {
          const tooltipTriggerList = document.querySelectorAll(
            '[data-bs-toggle="DefaultTooltipTwo"]'
          );
          const tooltipList = [...tooltipTriggerList].map(
            (tooltipTriggerEl) => new Tooltip(tooltipTriggerEl)
          );

          // Cleanup tooltips on unmount
          return () => {
            tooltipList.forEach((tooltip) => tooltip.dispose());
          };
        }
      );
    }
  }, []);
  return (
    <div className='col-lg-6'>
      <div className='card h-100 p-0'>
        <div className='card-header border-bottom bg-base py-16 px-24'>
          <h6 className='text-lg fw-semibold mb-0'>Default Tooltip</h6>
        </div>
        <div className='card-body p-24'>
          <div className='d-flex flex-wrap align-items-center gap-3'>
            <button
              type='button'
              className='btn text-secondary-light border input-form-dark radius-8 px-32 py-11'
              data-bs-toggle='DefaultTooltipTwo'
              data-bs-placement='top'
              data-bs-custom-class='tooltip-primary'
              data-bs-title='Primary Tooltip'
            >
              Tooltip On Top
            </button>
            <button
              type='button'
              className='btn text-secondary-light border input-form-dark radius-8 px-32 py-11'
              data-bs-toggle='DefaultTooltipTwo'
              data-bs-placement='right'
              data-bs-custom-class='tooltip-primary'
              data-bs-title='Primary Tooltip'
            >
              Tooltip On Right
            </button>
            <button
              type='button'
              className='btn text-secondary-light border input-form-dark radius-8 px-32 py-11'
              data-bs-toggle='DefaultTooltipTwo'
              data-bs-placement='left'
              data-bs-custom-class='tooltip-primary'
              data-bs-title='Primary Tooltip'
            >
              Tooltip On Left
            </button>
            <button
              type='button'
              className='btn text-secondary-light border input-form-dark radius-8 px-32 py-11'
              data-bs-toggle='DefaultTooltipTwo'
              data-bs-placement='bottom'
              data-bs-custom-class='tooltip-primary'
              data-bs-title='Primary Tooltip'
            >
              Tooltip On Bottom
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DefaultTooltipTwo;
