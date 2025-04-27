"use client"; 

import { useState } from "react";
import { Modal } from "./components/Modal"; 
import { getData, postData } from "./utils/crudData";
import { Section, EventDetails } from "./interfaces/eventDetails";
const urlRegex = /^https:\/\/www\.ticketmaster\.com\/[a-zA-Z0-9-]+\/event\/[a-zA-Z0-9-]+$/;

export default function Home() {
  const [isLoading, setIsLoading] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMessage, setModalMessage] = useState("");
  const [url, setUrl] = useState("");
  const [accessCode, setAccessCode] = useState("");
  const [isValid, setIsValid] = useState(true);
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({});
  let stopFetching = false;
  const hostUrl = "http://127.0.0.1:8000/api";

  const [eventData, setEventData] = useState<EventDetails | null>(null);

  const handleFormSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!urlRegex.test(url)) {
      setModalMessage("Ticketmaster URL tidak valid.");
      setIsModalOpen(true);
      return;
    }
    if (accessCode == "") {
      setModalMessage("Access code wajib diisi.");
      setIsModalOpen(true);
      return;
    }
    try {
      await handleShowEventData();
      return;
    } catch (error) {
      setIsLoading(false);
      setModalMessage("Error: " + error);
      setIsModalOpen(true);
      return;
    }
  };

  const toggleSection = (sectionId: string) => {
    setOpenSections((prev) => ({ ...prev, [sectionId]: !prev[sectionId] }));
  };
  const handleUrlChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setUrl(event.target.value);
    setIsValid(urlRegex.test(event.target.value));
    setIsValid(event.target.value !== "");
  };

  const handleAccessCodeChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    setAccessCode(event.target.value);
    setIsValid(event.target.value !== "");
  };

  const startFetching = async (hostUrl: string, taskId: string) => {
    if (stopFetching) return; // Stop if the flag is set to true
    const statusData = await getData(hostUrl + "/status/" + taskId);
    console.log("Status Data: ", statusData);
    switch (statusData.status) {
      case "scraped":
        console.log("Status Data Result: ", statusData.result);
        const eventData = await getData(
          hostUrl + "/result/" + statusData.result.result_file
        );
        setEventData(eventData);
        setIsLoading(false);
        setModalMessage(statusData.message);
        setIsModalOpen(true);
        stopFetching = true;
        break;
      case "error":
        setIsLoading(false);
        setModalMessage(statusData.message);
        setIsModalOpen(true);
        stopFetching = true;
        break;
    }
    // Set timeout for the next fetch after 10 seconds
    setTimeout(() => startFetching(hostUrl, taskId), 10000); // Recursive call to fetch data again
  };

  // Simulate showing event data
  const handleShowEventData = async () => {
    setIsLoading(true);
   
    const result = await postData(hostUrl + "/scrape", {
      url: url,
      code: accessCode,
    });
    console.log("Result Status: ", result.status);
    console.log("Result Task ID: ", result.task_id);
    switch (result.status) {
      case "pending":
        startFetching(hostUrl, result.task_id);
        break;
      case "success":
        setIsLoading(false);
        setModalMessage(result.message);
        setIsModalOpen(true);
        const eventData = await getData(
          hostUrl + "/result/" + result.result_file
        );
        setEventData(eventData);
        break;
      case "error":
        setIsLoading(false);
        setModalMessage(result.message);
        setIsModalOpen(true);
        break;
    }
  };

  const closeModal = () => {
    setIsModalOpen(false);
  };

  //customize
  const handleAutomateQueueClick = async (section:string,row:string) => {
    section = section.replace("Section:", "").trim();
    row = row.replace("Row: ", "").trim();
    
    console.log(url);
    console.log(section);
    console.log(row);
    const result = await postData(hostUrl + "/booking", {
       url,
      section,
      row:row,
    });
    console.log("Result Status: ", result.status);
    console.log("Result Task ID: ", result.task_id);
    // switch (result.status) {
    //   case "pending":
    //     startFetching(hostUrl, result.task_id);
    //     break;
    //   case "success":
    //     setIsLoading(false);
    //     setModalMessage(result.message);
    //     setIsModalOpen(true);
    //     break;
    //   case "error":
    //     setIsLoading(false);
    //     setModalMessage(result.message);
    //     setIsModalOpen(true);
    //     break;
    // }
    // try {
    //   const booking_response = await postData( hostUrl+ "/booking", {
    //     url: url,
    //     code: accessCode,
    //   });

    //   // const response = await axios.post("http://localhost:8000/api/scrape", requestData);

    //   if (booking_response.data.status === "pending") {
    //     // setSuccessMessage("Automate Queue started successfully!");
    //   }
    // } catch (error) {
    //   // setError("Error starting automate queue.");
    // } finally {
    //   setIsLoading(false);
    // }
  };
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-100 p-6 text-black">
      {isLoading && (
        <div className="absolute inset-0 flex justify-center items-center bg-gray-500 bg-opacity-50 z-1000">
          <div className="w-16 h-16 border-4 border-t-4 border-blue-500 border-solid rounded-full animate-spin"></div>
        </div>
      )}

      {!isLoading && (
        <div className="w-full max-w-4xl min-h-[80vh] p-6 my-10 bg-white shadow-lg rounded-lg border border-gray-300 flex flex-col">
          <h2 className="text-6xl font-bold mb-4 text-center font-serif">
            YEFTA
          </h2>

          <form onSubmit={handleFormSubmit}>
            <div className="flex flex-col sm:flex-row items-center sm:space-x-4 mb-4">
              <input
                type="text"
                className="border-2 border-gray-300 p-2 rounded w-full mb-4 sm:mb-0"
                value={url}
                onChange={handleUrlChange}
                placeholder="Enter a Ticketmaster URL"
              />
              <input
                type="text"
                className="border-2 border-gray-300 p-2 rounded w-auto mb-4 sm:mb-0"
                value={accessCode}
                onChange={handleAccessCodeChange}
                placeholder="Enter a Access Code"
              />
              <button
                type="submit"
                className={`bg-blue-500 text-white font-bold py-2 border-solid border-blue-700 border-2 px-4 min-w-[150px] rounded w-full sm:w-auto ${
                  !isValid ? "bg-red-500 border-red-700" : ""
                }`}
                disabled={isLoading}
              >
                {isLoading ? "LOADING..." : "GET DATA"}
              </button>
            </div>
          </form>

          {eventData && (
            <div className="bg-white bg-opacity-90 backdrop-blur-lg p-6 rounded-lg shadow-md">
              <h3 className="text-3xl font-bold text-indigo-600 mb-4">
                {eventData.title}
              </h3>
              <p className="text-lg">
                <strong>📅 Tanggal:</strong> {eventData.held_on}
              </p>
              <p className="text-lg">
                <strong>📍 Lokasi:</strong> {eventData.location}
              </p>

              {/* Section Info */}
              <div className="mt-4">
                <h3 className="text-xl font-bold mb-2">🎫 Tiket Tersedia:</h3>
                <p>
                  {eventData.count.section} Section, {eventData.count.row} Row
                </p>
              </div>

              {/* Recommended Seats */}
              <div className="mt-4">
                <h3 className="text-xl font-bold mb-2">
                  ✨ Rekomendasi Pilihan:
                </h3>
                {/* <ul className="list-disc pl-5">
                  {eventData.recommendations.map(
                    (recommendation: string, index: number) => (
                      <li key={index}>{recommendation}</li>
                    )
                  )}
                </ul> */}{" "}
                <ul className="list-disc pl-5">
                  {eventData.recommendations.map(
                    (recommendation: string, index: number) => {
                      // Menampilkan informasi section, row, dan harga dalam format yang diinginkan
                      const [section, row, price] = recommendation.split(", ");
                      const formattedPrice = price.replace("Harga: ", "");

                      return (
                        <div
                          key={index}
                          className="bg-white shadow-lg rounded-lg p-6 flex mb-2 justify-between items-center space-x-4"
                        >
                          <div>
                            <p className="text-lg font-semibold">{section}</p>
                            <p className="text-sm text-gray-600"> {row}</p>
                            <p className="text-xl font-bold text-blue-600">
                              {formattedPrice}
                            </p>
                          </div>
                          <button
                            onClick={() => handleAutomateQueueClick(section, row)}
                            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition duration-200"
                            disabled={isLoading}
                          >
                            {isLoading ? "Processing..." : "Automate Queue"}
                          </button>

                        </div>
                      );
                    }
                  )}
                </ul>
              </div>

              <div className="mt-4">
                {Object.entries(eventData.sections).map(
                  ([sectionId, section]) => (
                    <div
                      key={sectionId}
                      className="border-b shadow m-3 rounded overflow-hidden"
                    >
                      <button
                        onClick={() => toggleSection(sectionId)}
                        className="w-full flex justify-between items-center p-5 text-slate-800"
                      >
                        <h3 className="text-xl font-bold">
                          Section {sectionId}
                        </h3>
                        <span
                          className={`transition-transform duration-300 ${
                            openSections[sectionId] ? "rotate-180" : "rotate-0"
                          }`}
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            viewBox="0 0 16 16"
                            fill="currentColor"
                            className="w-4 h-4"
                          >
                            <path
                              fillRule="evenodd"
                              d="M11.78 9.78a.75.75 0 0 1-1.06 0L8 7.06 5.28 9.78a.75.75 0 0 1-1.06-1.06l3.25-3.25a.75.75 0 0 1 1.06 0l3.25 3.25a.75.75 0 0 1 0 1.06Z"
                              clipRule="evenodd"
                            />
                          </svg>
                        </span>
                      </button>
                      <div
                        className={`transition-all duration-500 ease-in-out ${
                          openSections[sectionId]
                            ? "max-h-96 opacity-100"
                            : "max-h-0 opacity-0"
                        }`}
                        style={{ overflow: "hidden" }}
                      >
                        <ul className="mt-2 space-y-4 p-5 max-h-[300px] overflow-y-auto bg-gray-50 rounded-lg shadow-md">
                          {section.rows.map((row, index) => (
                            <li
                              key={index}
                              className="flex justify-between items-center bg-white p-4 rounded-lg shadow-sm hover:shadow-md transition duration-200 ease-in-out"
                            >
                              <span className="text-lg text-gray-700">
                                🎟 Row {row.row} |{" "}
                                <strong className="text-blue-600">
                                  {section.currency} {row.price}
                                </strong>
                              </span>
                              <button
                                className="bg-green-500 text-white font-bold py-2 px-4 rounded-md hover:bg-green-600 transition duration-200"
                                onClick={() => handleAutomateQueueClick(sectionId, row.row)}
                                disabled={isLoading}
                              >
                                 {isLoading ? "Processing..." : "Automate Queue"}
                              </button>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {isModalOpen && <Modal message={modalMessage} onClose={closeModal} />}
    </div>
  );
}
